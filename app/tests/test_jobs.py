from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from accounts.models import LoginFailure, PlaceChangeRequest, PowChallenge, RegistrationIP, User
from adminpanel import audit
from adminpanel.models import AuditLog
from contacts import services as contacts
from contacts.models import ContactRequest
from jobs import cleanup, stats
from jobs.models import DailyStat

from .base import MUENSTER, RECKLINGHAUSEN, ROSENHEIM, BaseTest, make_admin, make_user


class CleanupTest(BaseTest):
    def test_retention_periods(self):
        now = timezone.now()
        user = make_user()
        RegistrationIP.objects.create(ip_hash="a", created_at=now - timedelta(days=8))
        RegistrationIP.objects.create(ip_hash="b", created_at=now - timedelta(days=6))
        LoginFailure.objects.create(account_hash="a", ip_hash="a", created_at=now - timedelta(hours=25))
        PowChallenge.objects.create(challenge="x" * 64, expires_at=now - timedelta(minutes=1))
        old = PlaceChangeRequest.objects.create(user=user, field="home", new_place_id=MUENSTER, decided_at=now - timedelta(days=31), decision="rejected")
        PlaceChangeRequest.objects.create(user=user, field="residence", new_place_id=MUENSTER, decided_at=now - timedelta(days=29), decision="rejected")
        open_request = PlaceChangeRequest.objects.create(user=user, field="home", new_place_id=RECKLINGHAUSEN, created_at=now - timedelta(days=90))
        admin = make_admin()
        audit.log(admin, "mute", user, "alt")
        AuditLog.objects.update(created_at=now - timedelta(days=732))
        audit.log(admin, "mute", user, "neu")

        cleanup.run()
        self.assertEqual(list(RegistrationIP.objects.values_list("ip_hash", flat=True)), ["b"])
        self.assertEqual((LoginFailure.objects.count(), PowChallenge.objects.count()), (0, 0))
        self.assertFalse(PlaceChangeRequest.objects.filter(pk=old.pk).exists())
        self.assertEqual(PlaceChangeRequest.objects.count(), 2)
        self.assertTrue(PlaceChangeRequest.objects.filter(pk=open_request.pk).exists())
        self.assertEqual(list(AuditLog.objects.values_list("reason", flat=True)), ["neu"])

    def test_withdrawn_requests_are_deleted_by_the_job(self):
        a, b = make_user(), make_user(residence=RECKLINGHAUSEN)
        request_id = contacts.send_request(a, b.id, "Hallo")["request_id"]
        contacts.withdraw_request(a, request_id)
        cleanup.run()
        self.assertTrue(ContactRequest.objects.filter(pk=request_id).exists())  # zählt heute noch zum Tageskontingent
        ContactRequest.objects.update(decided_at=timezone.now() - timedelta(days=2))
        cleanup.run()
        self.assertFalse(ContactRequest.objects.filter(pk=request_id).exists())

    def test_cleanup_never_touches_active_accounts(self):
        ids = {make_user().id, make_user(muted_until=timezone.now() + timedelta(hours=1)).id,
               make_user(status="suspended").id, make_user(status="pending", approval_required=True).id}
        call_command("aufraeumen", stdout=StringIO())
        self.assertEqual(set(User.objects.values_list("id", flat=True)), ids)


class StatsTest(BaseTest):
    def test_active_accounts_are_defined_by_activity_not_login(self):
        now = timezone.now()
        make_user(last_activity_at=now - timedelta(days=1))
        make_user(last_activity_at=now - timedelta(days=29), muted_until=now + timedelta(hours=1))
        make_user(last_activity_at=now - timedelta(days=31))
        make_user()  # nie aktiv gewesen
        make_user(status="suspended", last_activity_at=now)
        self.assertEqual(cleanup.snapshot_active_accounts(), 2)
        self.assertEqual(DailyStat.objects.get(day=timezone.localdate()).active_accounts, 2)

    def test_deletions_do_not_change_earlier_counts(self):
        a, b = make_user(), make_user(residence=RECKLINGHAUSEN)
        contacts.accept_request(b, contacts.send_request(a, b.id, "Hallo")["request_id"])
        from deletion.services import delete_account

        delete_account(a.id)
        row = DailyStat.objects.get(day=timezone.localdate())
        self.assertEqual((row.requests_sent, row.requests_accepted, row.conversations_started, row.deletions), (1, 1, 1, 1))
        self.assertEqual({f.name for f in DailyStat._meta.get_fields()} & {"user", "user_id", "text", "body"}, set())

    def test_pilot_report(self):
        now = timezone.now()
        make_user(last_activity_at=now)                              # Sonthofen, Marl
        make_user(last_activity_at=now, residence=RECKLINGHAUSEN)    # gleicher Landkreis, im Umkreis
        make_user(last_activity_at=now, home=ROSENHEIM)              # niemand aus dem Landkreis
        make_user(last_activity_at=now, residence=MUENSTER)          # gleicher Landkreis, aber außerhalb
        today = timezone.localdate()
        stats.bump("requests_sent", today - timedelta(days=20), 10)
        stats.bump("requests_accepted_cohort", today - timedelta(days=20), 5)
        stats.bump("requests_sent", today - timedelta(days=3), 100)  # außerhalb der Kohorte
        out = StringIO()
        call_command("pilotbericht", von=(today - timedelta(days=30)).isoformat(), bis=today.isoformat(), stdout=out)
        text = out.getvalue()
        self.assertIn("Aktive Konten: 4", text)
        self.assertIn("demselben Landkreis: 50.0 %", text)
        self.assertIn("Angenommene Anfragen: 50.0 %", text)
