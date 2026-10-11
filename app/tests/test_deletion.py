from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import PlaceChangeRequest, User
from adminpanel import audit
from contacts import services as contacts
from contacts.models import Block, ContactRequest, Conversation, Message, RequestAttempt
from deletion import journal
from deletion.services import delete_account
from jobs import cleanup
from moderation.models import Appeal, Report

from .base import PASSWORD, RECKLINGHAUSEN, Api, BaseTest, make_admin, make_user


class AccountDeletionTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.user, self.friend, self.other = make_user(), make_user(residence=RECKLINGHAUSEN), make_user()
        request_id = contacts.send_request(self.user, self.friend.id, "Hallo")["request_id"]
        self.conv = contacts.accept_request(self.friend, request_id)
        contacts.send_message(self.friend, self.conv.id, "Antwort der Gegenseite")
        contacts.send_request(self.other, self.user.id, "Offene Anfrage an das Konto")
        contacts.block(self.user, make_user().id)
        PlaceChangeRequest.objects.create(user=self.user, field="residence", new_place_id=RECKLINGHAUSEN, old_place_id=self.user.residence_id)
        # Meldung gegen das Konto und eine Meldung durch das Konto.
        Api(self.friend).post("/reports", {"target_type": "profile", "target_id": str(self.user.id), "reason": "spam"})
        Api(self.user).post("/reports", {"target_type": "profile", "target_id": str(self.friend.id), "reason": "other"})
        Appeal.objects.create(user=self.user, report=Report.objects.get(reported_user=self.user), text="Einspruch")

    def test_wrong_password_deletes_nothing(self):
        response = Api(self.user).post("/me/delete", {"password": "falsch"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(User.objects.get(pk=self.user.pk).status, "active")

    def test_account_is_invisible_at_once_and_fully_cleaned(self):
        since = timezone.now()
        api, second_session = Api(self.user), Api(self.user)
        self.assertEqual(api.post("/me/delete", {"password": PASSWORD}).status_code, 204)

        # Sofort: Grabstein, keine Kontodaten, alle Sitzungen ungültig.
        tomb = User.objects.get(pk=self.user.pk)
        self.assertEqual(tomb.status, "deleted")
        self.assertIsNotNone(tomb.deleted_at)
        for field in ("email", "password", "nickname", "birth_year", "adult_self_declared_at", "home_id", "residence_id",
                      "email_verified_at", "muted_until", "last_activity_at"):
            self.assertIsNone(getattr(tomb, field), field)
        self.assertFalse(api.get("/session").data["authenticated"])
        self.assertEqual(second_session.get("/requests").status_code, 401)
        self.assertEqual(Api().post("/auth/login", {"email": self.user.email, "password": PASSWORD}).status_code, 401)
        friend_api = Api(self.friend)
        self.assertEqual(friend_api.get(f"/users/{self.user.id}").status_code, 404)
        self.assertEqual(friend_api.get("/nearby/overview").data["total"], 2)  # vorher 3

        # Bereinigung: alles, was am Konto hing, ist weg, auch die Nachrichten der Gegenseite.
        uid = self.user.id
        self.assertFalse(Conversation.objects.filter(Q(user_a_id=uid) | Q(user_b_id=uid)).exists())
        self.assertEqual(Message.objects.count(), 0)
        self.assertFalse(ContactRequest.objects.filter(Q(from_user_id=uid) | Q(to_user_id=uid)).exists())
        self.assertFalse(RequestAttempt.objects.filter(Q(from_user_id=uid) | Q(to_user_id=uid)).exists())
        self.assertFalse(Block.objects.filter(Q(blocker_id=uid) | Q(blocked_id=uid)).exists())
        self.assertFalse(PlaceChangeRequest.objects.filter(user_id=uid).exists())
        self.assertFalse(Appeal.objects.filter(user_id=uid).exists())
        self.assertEqual(friend_api.get("/conversations").data["items"], [])
        self.assertEqual(friend_api.get(f"/conversations/{self.conv.id}/messages").status_code, 404)

        # Meldungen: die eigene verliert den Melder, die gegen das Konto wird geschlossen.
        by_user = Report.objects.get(reported_user=self.friend)
        against = Report.objects.get(reported_user_id=uid)
        self.assertIsNone(by_user.reporter_id)
        self.assertEqual((against.outcome, against.resolved_at is not None), ("account_deleted", True))

        # Journal: Auftrag steht drin, bestätigt, nur mit ID und Zeitstempel.
        entries = {(e["object_type"], e["object_id"]): e for e in journal.entries_since(since)}
        self.assertTrue(entries[("account", str(uid))]["confirmed"])
        self.assertTrue(entries[("conversation", str(self.conv.id))]["confirmed"])
        self.assertEqual(set(entries[("account", str(uid))]), {"object_type", "object_id", "requested_at", "confirmed"})

        # Die E-Mail-Adresse ist wieder frei.
        make_user(email=self.user.email)

    def test_tombstone_stays_while_referenced_and_goes_when_orphaned(self):
        delete_account(self.user.id)
        cleanup.run()
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())  # Meldung verweist noch darauf
        Report.objects.update(resolved_at=timezone.now() - timedelta(days=400))
        cleanup.run()  # löscht die Meldung, danach ist der Grabstein verwaist
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_tombstone_referenced_by_audit_log_goes_after_24_months_at_the_latest(self):
        admin = make_admin()
        lonely = make_user()
        audit.log(admin, "mute", lonely, "Test")
        delete_account(lonely.id)
        cleanup.run()
        self.assertTrue(User.objects.filter(pk=lonely.pk).exists())
        User.objects.filter(pk=lonely.pk).update(deleted_at=timezone.now() - timedelta(days=731))
        cleanup.run()
        self.assertFalse(User.objects.filter(pk=lonely.pk).exists())

    def test_database_forbids_tombstones_with_account_data(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=self.user.pk).update(status="deleted", deleted_at=timezone.now())

    def test_purge_is_repeatable(self):
        delete_account(self.user.id)
        call_command("loeschdienst", stdout=StringIO())
        call_command("loeschdienst", stdout=StringIO())


class JournalTest(BaseTest):
    def test_journal_is_append_only(self):
        import sqlite3
        from contextlib import closing

        from django.conf import settings

        journal.record("message", "11111111-1111-4111-8111-111111111111")
        with closing(sqlite3.connect(settings.DELETION_JOURNAL_PATH)) as conn:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("UPDATE deletion_journal SET object_id = 'x'")
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("DELETE FROM deletion_journal")
            columns = [row[1] for row in conn.execute("PRAGMA table_info(deletion_journal)")]
        self.assertEqual(columns, ["seq", "kind", "object_type", "object_id", "requested_at"])
        self.assertEqual(journal.purge(), 0)

    def test_unknown_object_types_are_rejected(self):
        with self.assertRaises(ValueError):
            journal.record("profile", "x")


class RestoreTest(BaseTest):
    """Der Fall aus Abschnitt 12: Montags-Backup, Löschung am Dienstag, Wiederherstellung am Mittwoch.

    Das Zurückspielen des Backups wird hier nachgestellt, indem die gelöschten
    Datensätze mit ihren alten Werten wieder eingefügt werden. Den Ablauf mit
    echtem ``pg_dump`` und ``pg_restore`` prüft ``ops/wiederherstellungstest.sh``.
    """

    def test_replay_deletes_again_what_was_deleted_after_the_backup(self):
        user, friend = make_user(), make_user(residence=RECKLINGHAUSEN)
        request_id = contacts.send_request(user, friend.id, "Hallo")["request_id"]
        conv = contacts.accept_request(friend, request_id)
        message = contacts.send_message(friend, conv.id, "Diese Nachricht lösche ich am Dienstag")
        pending = make_user(residence=RECKLINGHAUSEN)
        withdrawn_id = contacts.send_request(friend, pending.id, "Diese Anfrage ziehe ich zurück")["request_id"]
        untouched = make_user()

        # Montag: Backup.
        backup_time = timezone.now()
        snapshot = {
            "user": User.objects.filter(pk=user.pk).values().get(),
            "conversation": Conversation.objects.filter(pk=conv.pk).values().get(),
            "messages": list(Message.objects.filter(conversation=conv).values()),
        }

        # Dienstag: Löschungen.
        delete_account(user.id)
        contacts.withdraw_request(friend, withdrawn_id)
        other_conv = contacts.accept_request(pending, contacts.send_request(friend, pending.id, "Zweiter Versuch")["request_id"])
        own = contacts.send_message(friend, other_conv.id, "Gelöschte Nachricht")
        contacts.delete_message(friend, own["id"])

        # Mittwoch: Das Backup wird eingespielt (nachgestellt).
        User.objects.filter(pk=user.pk).delete()
        User.objects.create(**snapshot["user"])
        Conversation.objects.create(**snapshot["conversation"])
        Message.objects.bulk_create([Message(**row) for row in snapshot["messages"]])
        Message.objects.create(id=own["id"], conversation=other_conv, sender=friend, body="Gelöschte Nachricht")
        ContactRequest.objects.filter(pk=withdrawn_id).update(status="open", decided_at=None)
        self.assertEqual(User.objects.get(pk=user.pk).status, "active")  # ohne Nachlauf wäre das Konto wiederbelebt

        out = StringIO()
        call_command("wiederherstellung_nachlauf", backup_zeitpunkt=backup_time.isoformat(), stdout=out, stderr=out)

        restored = User.objects.get(pk=user.pk)
        self.assertEqual((restored.status, restored.email, restored.nickname), ("deleted", None, None))
        # Danach der Tagesjob; der Grabstein ist verwaist und verschwindet ganz.
        call_command("aufraeumen", stdout=out)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(Conversation.objects.filter(pk=conv.pk).exists())
        self.assertFalse(Message.objects.filter(pk=message["id"]).exists())
        self.assertFalse(Message.objects.filter(pk=own["id"]).exists())
        self.assertEqual(ContactRequest.objects.get(pk=withdrawn_id).status, "withdrawn")
        self.assertEqual(User.objects.get(pk=untouched.pk).status, "active")
        self.assertEqual(User.objects.get(pk=friend.pk).status, "active")
        self.assertIn("Konto gelöscht", out.getvalue())

    def test_entries_older_than_the_backup_are_not_replayed(self):
        user = make_user()
        journal.record("account", user.id)
        journal.confirm("account", user.id)
        out = StringIO()
        later = timezone.now() + timedelta(hours=1)
        call_command("wiederherstellung_nachlauf", backup_zeitpunkt=later.isoformat(), stdout=out, stderr=out)
        self.assertEqual(User.objects.get(pk=user.pk).status, "active")

    def test_unconfirmed_entries_are_reported_not_executed(self):
        user = make_user()
        since = timezone.now()
        journal.record("account", user.id)  # Auftrag eingetragen, aber nie ausgeführt
        out, err = StringIO(), StringIO()
        call_command("wiederherstellung_nachlauf", backup_zeitpunkt=since.isoformat(), stdout=out, stderr=err)
        self.assertEqual(User.objects.get(pk=user.pk).status, "active")
        self.assertIn(str(user.id), err.getvalue())
        call_command("wiederherstellung_nachlauf", backup_zeitpunkt=since.isoformat(), auch_unbestaetigte=True, stdout=out, stderr=err)
        self.assertEqual(User.objects.get(pk=user.pk).status, "deleted")
