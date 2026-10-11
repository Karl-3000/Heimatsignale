from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from contacts import services as contacts
from contacts.models import ContactRequest, Conversation, RequestAttempt
from heimatsignale.errors import ApiError
from jobs import cleanup
from jobs.models import DailyStat

from .base import RECKLINGHAUSEN, Api, BaseTest, make_user


class RequestStatesTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.a = make_user()
        self.b = make_user(residence=RECKLINGHAUSEN)
        self.api_a, self.api_b = Api(self.a), Api(self.b)

    def send(self, api=None, to=None, body="Hallo, ich komme auch aus dem Allgäu."):
        return (api or self.api_a).post("/requests", {"to_user_id": str((to or self.b).id), "body": body})

    def test_accept_creates_conversation_with_the_request_as_first_message(self):
        request_id = self.send().data["request_id"]
        incoming = self.api_b.get("/requests").data["incoming"]
        self.assertEqual([(r["id"], r["from"]["nickname"]) for r in incoming], [(request_id, self.a.nickname)])
        conv_id = self.api_b.post(f"/requests/{request_id}/accept").data["conversation_id"]
        messages = self.api_b.get(f"/conversations/{conv_id}/messages").data
        self.assertEqual([(m["body"], m["mine"]) for m in messages["messages"]], [("Hallo, ich komme auch aus dem Allgäu.", False)])
        self.assertEqual(self.api_a.get("/requests").data["outgoing"], [])
        self.assertEqual(self.send().data["code"], "connected")

    def test_body_rules(self):
        for body in ("", "   ", "x" * 501, "Schreib mir auf www.beispiel.de", "mehr unter https://x.y", "insta: name.com"):
            response = self.send(body=body)
            self.assertEqual(response.status_code, 422, body[:30])
        self.assertEqual(self.send(body="x" * 500).status_code, 201)

    def test_sender_cannot_tell_declined_from_open(self):
        request_id = self.send().data["request_id"]
        before = self.api_a.get("/requests").data
        self.assertEqual(self.api_b.post(f"/requests/{request_id}/decline").status_code, 204)
        after = self.api_a.get("/requests").data
        self.assertEqual(before["outgoing"], after["outgoing"])
        self.assertEqual(after["outgoing"][0]["state"], "open")
        self.assertEqual(before["quota"], after["quota"])
        self.assertEqual(self.api_a.get(f"/users/{self.b.id}").data["relation"]["outgoing_request"]["state"], "open")
        # Für den Empfänger ist sie erledigt.
        self.assertEqual(self.api_b.get("/requests").data["incoming"], [])
        self.assertEqual(self.api_b.post(f"/requests/{request_id}/accept").status_code, 404)

    def test_expiry_is_computed_from_the_timestamp_not_by_the_job(self):
        request_id = self.send().data["request_id"]
        ContactRequest.objects.filter(pk=request_id).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(ContactRequest.objects.get(pk=request_id).status, "open")  # der Job lief noch nicht
        self.assertEqual(self.api_b.get("/requests").data["incoming"], [])
        self.assertEqual(self.api_b.post(f"/requests/{request_id}/accept").status_code, 404)
        self.assertEqual(self.api_b.post(f"/requests/{request_id}/decline").status_code, 404)
        outgoing = self.api_a.get("/requests").data
        self.assertEqual(outgoing["outgoing"][0]["state"], "expired")
        self.assertEqual(outgoing["quota"]["active_used"], 0)
        # Der Job setzt nur nachträglich den Status und löscht nach weiteren 7 Tagen.
        cleanup.run()
        self.assertEqual(ContactRequest.objects.get(pk=request_id).status, "expired")
        ContactRequest.objects.filter(pk=request_id).update(expires_at=timezone.now() - timedelta(days=8))
        cleanup.run()
        self.assertFalse(ContactRequest.objects.filter(pk=request_id).exists())

    def test_declined_expires_like_open(self):
        request_id = self.send().data["request_id"]
        self.api_b.post(f"/requests/{request_id}/decline")
        ContactRequest.objects.filter(pk=request_id).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.api_a.get("/requests").data["outgoing"][0]["state"], "expired")

    def test_expiry_is_30_days(self):
        request_id = self.send().data["request_id"]
        req = ContactRequest.objects.get(pk=request_id)
        self.assertEqual(req.expires_at - req.created_at, timedelta(days=30))

    def test_withdraw_hides_it_and_frees_the_slot_immediately(self):
        request_id = self.send().data["request_id"]
        self.assertEqual(self.api_a.get("/requests").data["quota"]["active_used"], 1)
        self.assertEqual(self.api_b.post(f"/requests/{request_id}/withdraw").status_code, 404)
        self.assertEqual(self.api_a.post(f"/requests/{request_id}/withdraw").status_code, 204)
        self.assertEqual(self.api_a.get("/requests").data["quota"]["active_used"], 0)
        self.assertEqual(self.api_a.get("/requests").data["outgoing"], [])
        self.assertEqual(self.api_b.get("/requests").data["incoming"], [])
        self.assertEqual(self.api_b.post(f"/requests/{request_id}/accept").status_code, 404)

    def test_withdraw_works_for_declined_too(self):
        request_id = self.send().data["request_id"]
        self.api_b.post(f"/requests/{request_id}/decline")
        self.assertEqual(self.api_a.post(f"/requests/{request_id}/withdraw").status_code, 204)

    def test_at_most_two_attempts_per_direction_and_counter_survives_deletion(self):
        first = self.send().data["request_id"]
        self.assertEqual(self.send().data["code"], "already_requested")
        self.api_a.post(f"/requests/{first}/withdraw")
        second = self.send().data["request_id"]
        self.api_a.post(f"/requests/{second}/withdraw")
        ContactRequest.objects.all().delete()  # der Tagesjob hat die Anfragen gelöscht
        third = self.send()
        self.assertEqual((third.status_code, third.data["code"]), (409, "attempts_exhausted"))
        self.assertEqual(RequestAttempt.objects.get(from_user_id=self.a.id, to_user_id=self.b.id).count, 2)
        self.assertEqual(self.api_a.get(f"/users/{self.b.id}").data["relation"]["request_blocked_reason"], "attempts_exhausted")
        # Die Gegenrichtung ist weiterhin offen.
        self.assertEqual(self.send(api=self.api_b, to=self.a).status_code, 201)

    def test_mutual_requests_count_as_accepted(self):
        self.send()
        mutual = self.send(api=self.api_b, to=self.a, body="Das ist ja ein Zufall")
        self.assertEqual(mutual.status_code, 201)
        self.assertIsNone(mutual.data["request_id"])
        conv = Conversation.objects.get()
        self.assertEqual(str(conv.id), mutual.data["conversation_id"])
        self.assertEqual(ContactRequest.objects.get().status, "accepted")
        self.assertFalse(RequestAttempt.objects.filter(from_user_id=self.b.id).exists())

    def test_daily_quota_of_five(self):
        others = [make_user(residence=RECKLINGHAUSEN) for _ in range(6)]
        for other in others[:5]:
            self.assertEqual(self.send(to=other).status_code, 201)
        sixth = self.send(to=others[5])
        self.assertEqual((sixth.status_code, sixth.data["code"]), (400, "quota_daily"))
        # Am nächsten Kalendertag geht es weiter.
        ContactRequest.objects.update(created_at=timezone.now() - timedelta(days=1))
        self.assertEqual(self.send(to=others[5]).status_code, 201)

    def test_at_most_20_active_requests(self):
        others = [make_user(residence=RECKLINGHAUSEN) for _ in range(21)]
        now = timezone.now()
        ContactRequest.objects.bulk_create([
            ContactRequest(from_user=self.a, to_user=o, body="Hallo", created_at=now - timedelta(days=2),
                           expires_at=now + timedelta(days=28), status="declined" if i % 2 else "open")
            for i, o in enumerate(others[:20])
        ])
        full = self.send(to=others[20])
        self.assertEqual((full.status_code, full.data["code"]), (400, "quota_active"))
        first = ContactRequest.objects.filter(from_user=self.a).first()
        self.assertEqual(self.api_a.post(f"/requests/{first.id}/withdraw").status_code, 204)
        self.assertEqual(self.send(to=others[20]).status_code, 201)

    def test_partial_unique_index_allows_only_one_active_request_per_direction(self):
        now = timezone.now()
        kwargs = dict(from_user=self.a, to_user=self.b, body="Hallo", expires_at=now + timedelta(days=30))
        ContactRequest.objects.create(**kwargs)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ContactRequest.objects.create(**kwargs)
        ContactRequest.objects.update(status="declined")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ContactRequest.objects.create(**kwargs)
        ContactRequest.objects.update(status="withdrawn")
        ContactRequest.objects.create(**kwargs)
        ContactRequest.objects.create(**{**kwargs, "from_user": self.b, "to_user": self.a})

    def test_requests_are_private_to_their_two_parties(self):
        request_id = self.send().data["request_id"]
        stranger = Api(make_user())
        for action in ("accept", "decline", "withdraw"):
            self.assertEqual(stranger.post(f"/requests/{request_id}/{action}").status_code, 404, action)
        self.assertEqual(self.api_a.post(f"/requests/{request_id}/accept").status_code, 404)

    def test_no_request_to_oneself_or_unknown_ids(self):
        self.assertEqual(self.send(to=self.a).status_code, 404)
        self.assertEqual(self.api_a.post("/requests", {"to_user_id": "00000000-0000-4000-8000-000000000000", "body": "Hallo"}).status_code, 404)

    def test_daily_stats_count_creation_and_result(self):
        request_id = self.send().data["request_id"]
        self.api_b.post(f"/requests/{request_id}/accept")
        row = DailyStat.objects.get(day=timezone.localdate())
        self.assertEqual(
            (row.requests_sent, row.requests_accepted, row.requests_accepted_cohort, row.conversations_started), (1, 1, 1, 1)
        )

    def test_muted_sender_is_rejected_in_the_service_too(self):
        self.a.muted_until = timezone.now() + timedelta(hours=1)
        self.a.save()
        with self.assertRaises(ApiError) as ctx:
            contacts.send_request(self.a, self.b.id, "Hallo")
        self.assertEqual(ctx.exception.code, "muted")
