from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from contacts import services as contacts
from contacts.models import Conversation, Message
from deletion import journal
from jobs.models import DailyStat

from .base import RECKLINGHAUSEN, Api, BaseTest, make_user


class ConversationTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.a, self.b = make_user(), make_user(residence=RECKLINGHAUSEN)
        self.stranger = make_user()
        request_id = contacts.send_request(self.a, self.b.id, "Hallo")["request_id"]
        self.conv = contacts.accept_request(self.b, request_id)
        self.api_a, self.api_b = Api(self.a), Api(self.b)
        self.path = f"/conversations/{self.conv.id}/messages"

    def test_strangers_have_no_access_to_messages(self):
        api = Api(self.stranger)
        self.assertEqual(api.get(self.path).status_code, 404)
        self.assertEqual(api.post(self.path, {"body": "Ich lese mit"}).status_code, 404)
        message_id = Message.objects.get().id
        self.assertEqual(api.delete(f"/messages/{message_id}").status_code, 404)
        self.assertEqual(api.get("/conversations").data["items"], [])
        self.assertEqual(Api().get(self.path).status_code, 401)
        self.assertEqual(Message.objects.count(), 1)

    def test_no_conversation_without_an_accepted_request(self):
        c = make_user(residence=RECKLINGHAUSEN)
        contacts.send_request(self.a, c.id, "Hallo")
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(len(Api(c).get("/conversations").data["items"]), 0)

    def test_plain_text_only_and_length(self):
        self.assertEqual(self.api_a.post(self.path, {"body": ""}).status_code, 422)
        self.assertEqual(self.api_a.post(self.path, {"body": "x" * 2001}).status_code, 422)
        sent = self.api_a.post(self.path, {"body": "<img src=x> bleibt Text"})
        self.assertEqual(sent.data["body"], "<img src=x> bleibt Text")
        self.assertEqual(set(sent.data), {"id", "mine", "body", "created_at"})

    def test_links_only_after_ten_messages(self):
        link = {"body": "Schau mal: https://beispiel.de/fest"}
        self.assertEqual(self.api_a.post(self.path, link).status_code, 422)
        self.assertFalse(self.api_a.get(self.path).data["links_allowed"])
        for i in range(9):
            (self.api_a if i % 2 else self.api_b).post(self.path, {"body": f"Nachricht {i}"})
        self.assertTrue(self.api_a.get(self.path).data["links_allowed"])
        self.assertEqual(self.api_a.post(self.path, link).status_code, 201)

    @override_settings(MESSAGES_PER_HOUR=3)
    def test_rate_limit_per_conversation(self):
        self.assertEqual(self.api_a.post(self.path, {"body": "zwei"}).status_code, 201)
        self.assertEqual(self.api_b.post(self.path, {"body": "drei"}).status_code, 201)
        limited = self.api_a.post(self.path, {"body": "vier"})
        self.assertEqual((limited.status_code, limited.data["code"]), (429, "rate_limited"))
        Message.objects.update(created_at=timezone.now() - timedelta(minutes=61))
        self.assertEqual(self.api_a.post(self.path, {"body": "vier"}).status_code, 201)

    def test_deleting_own_message_removes_it_for_both_and_is_journaled(self):
        since = timezone.now()
        mine = self.api_a.post(self.path, {"body": "Das nehme ich zurück"}).data["id"]
        self.assertEqual(self.api_b.delete(f"/messages/{mine}").status_code, 404)
        self.assertEqual(self.api_a.delete(f"/messages/{mine}").status_code, 204)
        for api in (self.api_a, self.api_b):
            self.assertNotIn(mine, [m["id"] for m in api.get(self.path).data["messages"]])
        entry = [e for e in journal.entries_since(since) if e["object_id"] == mine]
        self.assertEqual([(e["object_type"], e["confirmed"]) for e in entry], [("message", True)])

    def test_blocking_ends_the_conversation_for_both_at_once(self):
        self.assertEqual(self.api_b.post("/blocks", {"user_id": str(self.a.id)}).status_code, 204)
        for api in (self.api_a, self.api_b):
            data = api.get(self.path).data
            self.assertEqual((data["available"], data["messages"], data["partner"]), (False, [], None))
            self.assertEqual(api.post(self.path, {"body": "Hallo?"}).data["code"], "unavailable")
            item = api.get("/conversations").data["items"][0]
            self.assertEqual((item["available"], item["partner"], item["last_message"]), (False, None, None))
        self.assertEqual(self.api_a.get("/inbox/summary").data["conversations"], [])
        # Die Blockliste nennt die Person, und Entblocken öffnet das Gespräch nicht wieder.
        self.assertEqual([b["user_id"] for b in self.api_b.get("/blocks").data["items"]], [str(self.a.id)])
        self.assertEqual(self.api_b.delete(f"/blocks/{self.a.id}").status_code, 204)
        self.assertFalse(self.api_a.get(self.path).data["available"])

    def test_blocking_withdraws_open_requests_between_both(self):
        c = make_user(residence=RECKLINGHAUSEN)
        contacts.send_request(self.a, c.id, "Hallo")
        Api(c).post("/blocks", {"user_id": str(self.a.id)})
        self.assertEqual(self.api_a.get("/requests").data["outgoing"], [])
        self.assertEqual(self.api_a.get("/requests").data["quota"]["active_used"], 0)
        self.assertEqual(self.api_a.post("/requests", {"to_user_id": str(c.id), "body": "Nochmal"}).status_code, 404)

    def test_no_read_receipts_or_online_status_anywhere(self):
        self.api_b.get(self.path)
        blob = str(self.api_a.get(self.path).data) + str(self.api_a.get("/conversations").data) + str(
            self.api_a.get(f"/users/{self.b.id}").data
        ) + str(self.api_a.get("/inbox/summary").data)
        for forbidden in ("read_at", "seen", "online", "last_activity", "last_seen", "email", "birth"):
            self.assertNotIn(forbidden, blob)

    def test_pagination_has_a_fixed_page_size(self):
        Message.objects.bulk_create([
            Message(conversation=self.conv, sender=self.a, body=f"n{i}", created_at=timezone.now() + timedelta(seconds=i + 1))
            for i in range(60)
        ])
        first = self.api_a.get(self.path, limit=1000).data
        self.assertEqual((len(first["messages"]), first["has_more"]), (50, True))
        older = self.api_a.get(self.path, before=first["messages"][0]["id"]).data
        self.assertEqual((len(older["messages"]), older["has_more"]), (11, False))

    def test_recurring_conversation_is_counted_once(self):
        start = self.conv.created_at
        for day in range(3):
            for sender in (self.a, self.b):
                Message.objects.create(conversation=self.conv, sender=sender, body="x", created_at=start + timedelta(days=day, hours=1))
        self.api_a.post(self.path, {"body": "bis bald"})
        self.api_b.post(self.path, {"body": "bis bald"})
        row = DailyStat.objects.get(day=timezone.localdate())
        self.assertEqual((row.conversations_recurring, row.conversations_recurring_cohort), (1, 1))
