"""Tatsächlich parallele Aktionen (PROJEKT.md, Abschnitt 7).

Jeder Thread hat seine eigene Datenbankverbindung und damit seine eigene
Transaktion. Eine Barriere lässt alle gleichzeitig los.
"""

from datetime import timedelta
from threading import Barrier, Thread

from django.db import connection
from django.utils import timezone

from contacts import services as contacts
from contacts.models import Block, ContactRequest, Conversation, Message, RequestAttempt
from heimatsignale.errors import ApiError

from .base import RECKLINGHAUSEN, ParallelTest, make_user


def run_parallel(calls):
    """Führt die Aufrufe gleichzeitig aus und liefert pro Aufruf Ergebnis oder Fehlercode."""
    barrier = Barrier(len(calls))
    results = [None] * len(calls)

    def worker(index, call):
        try:
            barrier.wait(timeout=10)
            results[index] = ("ok", call())
        except ApiError as exc:
            results[index] = ("error", exc.code)
        except Exception as exc:  # unerwartet: im Test sichtbar machen
            results[index] = ("crash", repr(exc))
        finally:
            connection.close()

    threads = [Thread(target=worker, args=(i, c)) for i, c in enumerate(calls)]
    [t.start() for t in threads]
    [t.join(timeout=30) for t in threads]
    return results


def kinds(results):
    return sorted(r[0] if r[0] != "error" else r[1] for r in results)


class ParallelRequestsTest(ParallelTest):
    def setUp(self):
        super().setUp()
        self.a = make_user()
        self.b = make_user(residence=RECKLINGHAUSEN)

    def test_same_request_twice_at_once_creates_exactly_one(self):
        for _ in range(3):
            ContactRequest.objects.all().delete()
            RequestAttempt.objects.all().delete()
            results = run_parallel([lambda: contacts.send_request(self.a, self.b.id, "Hallo")] * 4)
            self.assertEqual(kinds(results), ["already_requested"] * 3 + ["ok"], results)
            self.assertEqual(ContactRequest.objects.count(), 1)
            self.assertEqual(RequestAttempt.objects.get().count, 1)

    def test_parallel_requests_cannot_exceed_the_daily_quota(self):
        others = [make_user(residence=RECKLINGHAUSEN) for _ in range(8)]
        results = run_parallel([(lambda o=o: contacts.send_request(self.a, o.id, "Hallo")) for o in others])
        self.assertEqual(kinds(results), ["ok"] * 5 + ["quota_daily"] * 3, results)
        self.assertEqual(ContactRequest.objects.filter(from_user=self.a).count(), 5)

    def test_parallel_requests_cannot_take_the_same_last_active_slot(self):
        now = timezone.now()
        fillers = [make_user(residence=RECKLINGHAUSEN) for _ in range(19)]
        ContactRequest.objects.bulk_create([
            ContactRequest(from_user=self.a, to_user=o, body="Hallo", created_at=now - timedelta(days=3),
                           expires_at=now + timedelta(days=27)) for o in fillers
        ])
        others = [make_user(residence=RECKLINGHAUSEN) for _ in range(4)]
        results = run_parallel([(lambda o=o: contacts.send_request(self.a, o.id, "Hallo")) for o in others])
        self.assertEqual(kinds(results), ["ok"] + ["quota_active"] * 3, results)
        self.assertEqual(ContactRequest.objects.filter(from_user=self.a, status="open").count(), 20)

    def test_attempt_counter_never_exceeds_two(self):
        RequestAttempt.objects.create(from_user=self.a, to_user=self.b, count=1)
        results = run_parallel([lambda: contacts._take_attempt(self.a.id, self.b.id)] * 6)
        self.assertEqual([r[1] for r in results].count(True), 1, results)
        self.assertEqual(RequestAttempt.objects.get().count, 2)

    def test_double_accept_creates_one_conversation(self):
        request_id = contacts.send_request(self.a, self.b.id, "Hallo")["request_id"]
        results = run_parallel([lambda: contacts.accept_request(self.b, request_id).id] * 4)
        self.assertEqual(kinds(results), ["not_found"] * 3 + ["ok"], results)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)

    def test_crossing_requests_end_in_exactly_one_conversation(self):
        for _ in range(3):
            Conversation.objects.all().delete()
            ContactRequest.objects.all().delete()
            RequestAttempt.objects.all().delete()
            results = run_parallel([
                lambda: contacts.send_request(self.a, self.b.id, "Hallo von A"),
                lambda: contacts.send_request(self.b, self.a.id, "Hallo von B"),
            ])
            self.assertEqual(kinds(results), ["ok", "ok"], results)
            self.assertEqual(Conversation.objects.count(), 1)
            self.assertEqual(ContactRequest.objects.filter(status="accepted").count(), 1)
            self.assertEqual(ContactRequest.objects.filter(status__in=["open", "declined"]).count(), 0)

    def test_accept_and_block_at_once_never_leave_an_open_conversation_with_a_block(self):
        for _ in range(4):
            Block.objects.all().delete()
            Conversation.objects.all().delete()
            ContactRequest.objects.all().delete()
            RequestAttempt.objects.all().delete()
            request_id = contacts.send_request(self.a, self.b.id, "Hallo")["request_id"]
            results = run_parallel([
                lambda: contacts.accept_request(self.b, request_id).id,
                lambda: contacts.block(self.a, self.b.id),
            ])
            self.assertNotIn("crash", [r[0] for r in results], results)
            self.assertTrue(Block.objects.exists())
            # Entweder wurde gar nicht angenommen, oder das Gespräch ist beendet.
            self.assertFalse(Conversation.objects.filter(blocked=False).exists(), results)
            self.assertFalse(ContactRequest.objects.filter(status__in=["open", "declined"]).exists())

    def test_message_and_block_at_once_are_serialised(self):
        request_id = contacts.send_request(self.a, self.b.id, "Hallo")["request_id"]
        conv = contacts.accept_request(self.b, request_id)
        results = run_parallel([
            lambda: contacts.send_message(self.a, conv.id, "Noch eine Nachricht"),
            lambda: contacts.block(self.b, self.a.id),
        ])
        self.assertNotIn("crash", [r[0] for r in results], results)
        self.assertIn(kinds(results), (["ok", "ok"], ["ok", "unavailable"]))
        conv.refresh_from_db()
        self.assertTrue(conv.blocked)
        # Nach dem Blockieren kommt nichts mehr durch.
        with self.assertRaises(ApiError):
            contacts.send_message(self.a, conv.id, "Und jetzt?")

    def test_parallel_blocks_in_both_directions_do_not_deadlock(self):
        results = run_parallel([lambda: contacts.block(self.a, self.b.id), lambda: contacts.block(self.b, self.a.id)])
        # Wer zuerst blockiert, macht sich für die andere Seite unsichtbar; deren Versuch
        # endet dann sauber mit "nicht gefunden". Entscheidend: keine Verklemmung.
        self.assertIn(kinds(results), (["ok", "ok"], ["not_found", "ok"]), results)
        self.assertIn(Block.objects.count(), (1, 2))
