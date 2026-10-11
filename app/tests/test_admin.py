from datetime import timedelta
from io import StringIO

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.models import InviteCode, Moderator, PlaceChangeRequest, User
from adminpanel.models import AuditLog
from moderation.models import Report

from .base import MUENSTER, PASSWORD, RECKLINGHAUSEN, Api, BaseTest, make_admin, make_user

ADMIN = f"/{settings.ADMIN_PATH}"


def otp_client(admin: User) -> Client:
    """Admin-Sitzung mit bestätigtem zweiten Faktor."""
    device = TOTPDevice.objects.create(user=admin, name="Test", confirmed=True)
    client = Client()
    token = totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits)
    response = client.post(f"{ADMIN}/login/", {
        "username": admin.email, "password": PASSWORD, "otp_device": device.persistent_id, "otp_token": f"{token:06d}",
    })
    assert response.status_code == 302, response.content[:300]
    return client


def run_action(client, model: str, action: str, ids, reason=""):
    return client.post(f"{ADMIN}/{model}/", {"action": action, "_selected_action": [str(i) for i in ids], "reason": reason}, follow=True)


class AdminAccessTest(BaseTest):
    def test_admin_area_lives_under_its_own_path_and_needs_two_factors(self):
        admin = make_admin()
        self.assertEqual(Client().get("/admin/").status_code, 404)
        client = Client()
        self.assertEqual(client.get(f"{ADMIN}/").status_code, 302)
        # Passwort allein genügt nicht.
        client.post(f"{ADMIN}/login/", {"username": admin.email, "password": PASSWORD})
        self.assertEqual(client.get(f"{ADMIN}/").status_code, 302)
        client.force_login(admin, backend="accounts.backends.ThrottledBackend")
        self.assertEqual(client.get(f"{ADMIN}/").status_code, 302)
        self.assertEqual(otp_client(admin).get(f"{ADMIN}/").status_code, 200)

    def test_ordinary_users_cannot_enter(self):
        user = make_user()
        device = TOTPDevice.objects.create(user=user, name="Test", confirmed=True)
        token = totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits)
        client = Client()
        client.post(f"{ADMIN}/login/", {"username": user.email, "password": PASSWORD,
                                        "otp_device": device.persistent_id, "otp_token": f"{token:06d}"})
        self.assertEqual(client.get(f"{ADMIN}/").status_code, 302)

    def test_admin_login_obeys_the_login_rules(self):
        admin = make_admin()
        client = Client()
        for _ in range(5):
            client.post(f"{ADMIN}/login/", {"username": admin.email, "password": "falsch"})
        response = client.post(f"{ADMIN}/login/", {"username": admin.email, "password": PASSWORD})
        self.assertEqual(response.status_code, 200)  # Formular erneut, keine Anmeldung
        self.assertNotIn("_auth_user_id", client.session)

    def test_admin_session_cannot_use_the_app_api(self):
        api = Api(make_admin())
        response = api.get("/nearby/overview")
        self.assertEqual((response.status_code, response.data["code"]), (403, "staff_only_admin"))
        self.assertTrue(api.get("/session").data["user"]["is_staff"])

    def test_setup_command_creates_admin_with_totp_and_backup_codes(self):
        import os
        from unittest import mock

        out = StringIO()
        with mock.patch.dict(os.environ, {"ADMIN_PASSWORD": "ein-sehr-langes-admin-passwort"}):
            call_command("admin_anlegen", email="Chef@Example.org", ohne_rueckfragen=True, stdout=out)
        admin = User.objects.get(email="chef@example.org")
        self.assertEqual((admin.status, admin.moderator.role, admin.is_superuser), ("active", "admin", True))
        self.assertIsNone(admin.home_id)
        self.assertTrue(TOTPDevice.objects.filter(user=admin, confirmed=True).exists())
        self.assertIn("otpauth://totp/", out.getvalue())
        self.assertEqual(admin.staticdevice_set.get().token_set.count(), 8)
        # Admin-Konten erscheinen nie im Umkreis.
        self.assertEqual(Api(make_user()).get("/nearby/overview").data["total"], 0)


class AdminActionsTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.admin = make_admin()
        self.client = otp_client(self.admin)
        self.user = make_user()

    def test_pages_render(self):
        Api(make_user()).post("/reports", {"target_type": "profile", "target_id": str(self.user.id), "reason": "spam"})
        for path in ("", "accounts/user/", f"accounts/user/{self.user.id}/change/", "accounts/user/?zustand=freigabe",
                     "moderation/report/", f"moderation/report/{Report.objects.get().id}/change/", "moderation/appeal/",
                     "accounts/placechangerequest/", "accounts/invitecode/", "accounts/invitecode/add/", "jobs/dailystat/",
                     "adminpanel/auditlog/", "places/place/?q=marl", "otp_totp/totpdevice/", f"accounts/user/{self.user.id}/ort/"):
            self.assertEqual(self.client.get(f"{ADMIN}/{path}").status_code, 200, path)

    def test_changing_a_place_needs_a_reason_and_audits_without_place_values(self):
        url = f"{ADMIN}/accounts/user/{self.user.id}/ort/"
        missing = self.client.post(url, {"field": "residence", "place": MUENSTER, "reason": ""})
        self.assertEqual(missing.status_code, 200)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.residence_id, MUENSTER)

        self.assertEqual(self.client.post(url, {"field": "residence", "place": "Münster", "reason": "Umzug belegt"}).status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.residence_id, MUENSTER)
        entry = AuditLog.objects.get(action="change_residence")
        self.assertEqual((entry.admin_id, entry.target_user_id, entry.reason), (self.admin.id, self.user.id, "Umzug belegt"))
        text = " ".join(str(v) for v in AuditLog.objects.values_list("action", "reason").get(pk=entry.pk))
        for forbidden in ("Münster", MUENSTER, "Marl", self.user.email):
            self.assertNotIn(forbidden, text)
        self.assertEqual({f.name for f in AuditLog._meta.get_fields()}, {"id", "admin", "action", "target_user", "reason", "created_at"})

    def test_place_change_request_keeps_old_value_until_decided(self):
        req = PlaceChangeRequest.objects.create(user=self.user, field="residence", new_place_id=RECKLINGHAUSEN,
                                                old_place_id=self.user.residence_id)
        other = PlaceChangeRequest.objects.create(user=self.user, field="home", new_place_id=MUENSTER,
                                                  old_place_id=self.user.home_id)
        with self.captureOnCommitCallbacks(execute=True):
            run_action(self.client, "accounts/placechangerequest", "approve", [req.id])
            run_action(self.client, "accounts/placechangerequest", "reject", [other.id])
        self.user.refresh_from_db()
        self.assertEqual((self.user.residence_id, self.user.home_id), (RECKLINGHAUSEN, "09780139"))
        self.assertEqual(set(PlaceChangeRequest.objects.values_list("decision", flat=True)), {"approved", "rejected"})
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(AuditLog.objects.filter(action__startswith="place_change_").count(), 2)

    def test_approval_queue(self):
        queued = make_user(status="pending", approval_required=True)
        page = self.client.get(f"{ADMIN}/accounts/user/?zustand=freigabe")
        self.assertContains(page, queued.nickname)
        self.assertNotContains(page, self.user.nickname)
        with self.captureOnCommitCallbacks(execute=True):
            run_action(self.client, "accounts/user", "approve", [queued.id])
        queued.refresh_from_db()
        self.assertEqual(queued.status, "active")
        self.assertIn("freigegeben", mail.outbox[-1].body)

    def test_mute_suspend_unsuspend_and_delete_with_audit(self):
        run_action(self.client, "accounts/user", "suspend", [self.user.id])  # ohne Begründung: nichts passiert
        self.assertEqual(User.objects.get(pk=self.user.pk).status, "active")
        run_action(self.client, "accounts/user", "mute_48h", [self.user.id], "Ton")
        self.assertGreater(User.objects.get(pk=self.user.pk).muted_until, timezone.now() + timedelta(hours=47))
        run_action(self.client, "accounts/user", "unmute", [self.user.id])
        run_action(self.client, "accounts/user", "suspend", [self.user.id], "Verstoß")
        self.assertEqual(User.objects.get(pk=self.user.pk).status, "suspended")
        run_action(self.client, "accounts/user", "unsuspend", [self.user.id])
        self.assertEqual(User.objects.get(pk=self.user.pk).status, "active")
        run_action(self.client, "accounts/user", "delete_accounts", [self.user.id], "auf Wunsch")
        self.assertEqual(User.objects.get(pk=self.user.pk).status, "deleted")
        self.assertEqual(
            list(AuditLog.objects.order_by("created_at").values_list("action", flat=True)),
            ["mute", "unmute", "suspend", "unsuspend", "delete_account"],
        )

    def test_report_queue_is_sorted_by_severity_and_resolves_whole_incidents(self):
        a, b = make_user(), make_user()
        Api(make_user()).post("/reports", {"target_type": "profile", "target_id": str(a.id), "reason": "other"})
        for _ in range(2):
            Api(make_user()).post("/reports", {"target_type": "profile", "target_id": str(b.id), "reason": "harassment"})
        page = self.client.get(f"{ADMIN}/moderation/report/")
        content = page.content.decode()
        self.assertLess(content.index("Belästigung"), content.index("Sonstiges"))
        one = Report.objects.filter(reported_user=b).first()
        with self.captureOnCommitCallbacks(execute=True):
            run_action(self.client, "moderation/report", "confirm", [one.id], "eindeutig")
        self.assertEqual(Report.objects.filter(reported_user=b, outcome="confirmed", resolved_by=self.admin).count(), 2)
        self.assertEqual(User.objects.get(pk=b.pk).status, "suspended")

    def test_invite_codes_can_be_created(self):
        response = self.client.post(f"{ADMIN}/accounts/invitecode/add/", {
            "label": "Erstsemesterwoche", "valid_until_0": "31.12.2030", "valid_until_1": "23:59:00", "max_uses": "200",
        })
        self.assertEqual(response.status_code, 302, response.content[:500])
        code = InviteCode.objects.get()
        self.assertEqual((code.created_by_id, code.used_count, len(code.code)), (self.admin.id, 0, 14))

    def test_moderators_see_reports_but_cannot_change_places_or_delete(self):
        moderator = make_admin(role="moderator")
        client = otp_client(moderator)
        self.assertEqual(client.get(f"{ADMIN}/moderation/report/").status_code, 200)
        self.assertEqual(client.get(f"{ADMIN}/accounts/invitecode/").status_code, 403)
        self.assertEqual(client.get(f"{ADMIN}/accounts/user/{self.user.id}/ort/").status_code, 302)
        run_action(client, "accounts/user", "delete_accounts", [self.user.id], "Versuch")
        self.assertEqual(User.objects.get(pk=self.user.pk).status, "active")
        self.assertEqual(Moderator.objects.count(), 2)
