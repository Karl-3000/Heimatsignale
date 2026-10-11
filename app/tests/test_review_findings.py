"""Regressionstests zu den Befunden der unabhängigen Durchsicht."""

from datetime import timedelta
from threading import Barrier, Thread

from django.db import connection
from django.test import Client
from django.utils import timezone

from accounts.models import LoginFailure, Moderator, RegistrationIP, User
from accounts.net import account_hash, ip_hash
from adminpanel.models import AuditLog
from contacts import services as contacts
from contacts.models import ContactRequest, Conversation
from deletion.services import delete_account
from jobs import cleanup
from moderation import services as moderation
from moderation.models import Appeal, Report

from .base import (
    LEIPZIG, MARL, MUENSTER, PASSWORD, RECKLINGHAUSEN, SONTHOFEN, Api, BaseTest, ParallelTest, make_admin, make_user,
    solved_pow,
)
from .test_admin import ADMIN, otp_client, run_action
from .test_concurrency import kinds, run_parallel


class BlockIsNoBackdoorTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.a, self.b = make_user(), make_user(residence=RECKLINGHAUSEN)

    def test_blocked_person_cannot_keep_watching_by_blocking_back(self):
        contacts.block(self.b, self.a.id)
        api = Api(self.a)
        self.assertEqual(api.get(f"/users/{self.b.id}").status_code, 404)
        self.assertEqual(api.post("/blocks", {"user_id": str(self.b.id)}).status_code, 404)
        self.assertEqual(api.get(f"/users/{self.b.id}").status_code, 404)
        self.assertEqual(api.get("/blocks").data["items"], [])

    def test_own_block_hides_the_profile_too(self):
        api = Api(self.a)
        self.assertEqual(api.post("/blocks", {"user_id": str(self.b.id)}).status_code, 204)
        User.objects.filter(pk=self.b.pk).update(residence_id=MUENSTER)
        self.assertEqual(api.get(f"/users/{self.b.id}").status_code, 404)

    def test_only_known_accounts_can_be_blocked(self):
        api = Api(self.a)
        far = make_user(residence=LEIPZIG)
        others = [far, make_user(status="pending", verified=False), make_user(status="pending", approval_required=True),
                  make_user(status="suspended"), make_admin()]
        for other in others:
            self.assertEqual(api.post("/blocks", {"user_id": str(other.id)}).status_code, 404, other.status)
        self.assertEqual(api.get("/blocks").data["items"], [])
        # Und damit auch kein Melden und kein Stummschalten aus der Ferne.
        self.assertEqual(api.post("/reports", {"target_type": "profile", "target_id": str(far.id), "reason": "spam"}).status_code, 404)

    def test_someone_from_a_conversation_can_still_be_blocked_after_moving_away(self):
        contacts.accept_request(self.b, contacts.send_request(self.a, self.b.id, "Hallo")["request_id"])
        User.objects.filter(pk=self.b.pk).update(residence_id=MUENSTER)
        self.assertEqual(Api(self.a).post("/blocks", {"user_id": str(self.b.id)}).status_code, 204)


class RequestPrivacyTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.a, self.b = make_user(), make_user(residence=RECKLINGHAUSEN)

    def test_request_lists_follow_the_radius(self):
        contacts.send_request(self.a, self.b.id, "Hallo")
        User.objects.filter(pk=self.b.pk).update(residence_id=LEIPZIG)
        self.assertEqual(Api(self.a).get("/requests").data["outgoing"], [])
        self.assertEqual(Api(self.b).get("/requests").data["incoming"], [])
        self.assertEqual(Api(self.b).get("/inbox/summary").data["incoming_requests"], 0)

    def test_counter_request_after_decline_does_not_reveal_the_decline(self):
        request_id = contacts.send_request(self.a, self.b.id, "Hallo")["request_id"]
        contacts.decline_request(self.b, request_id)
        result = Api(self.b).post("/requests", {"to_user_id": str(self.a.id), "body": "Doch gern"}).data
        self.assertIsNotNone(result["conversation_id"])
        data = Api(self.a).get("/requests").data
        self.assertEqual((data["incoming"], data["outgoing"]), ([], []))
        self.assertEqual(Conversation.objects.count(), 1)

    def test_withdrawing_an_expired_request_is_not_found(self):
        request_id = contacts.send_request(self.a, self.b.id, "Hallo")["request_id"]
        ContactRequest.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        api = Api(self.a)
        self.assertEqual(api.post(f"/requests/{request_id}/withdraw").status_code, 404)
        self.assertEqual(api.get("/requests").data["outgoing"][0]["state"], "expired")

    def test_reported_request_keeps_its_text_after_acceptance(self):
        request_id = contacts.send_request(self.a, self.b.id, "Na, Lust auf mehr?")["request_id"]
        contacts.accept_request(self.b, request_id)
        Api(self.b).post("/reports", {"target_type": "request", "target_id": request_id, "reason": "dating"})
        self.assertEqual(Report.objects.get().snapshot["text"], "Na, Lust auf mehr?")

    def test_nickname_is_fixed_once_one_acts_visibly(self):
        fresh = make_user(nickname_rerolls_left=1)
        api = Api(fresh)
        api.get("/nearby/people", home=SONTHOFEN)
        self.assertEqual(api.post("/me/nickname/reroll").data["code"], "reroll_used")
        fresh2 = make_user(nickname_rerolls_left=1)
        Api(fresh2).post("/requests", {"to_user_id": str(self.b.id), "body": "Hallo"})
        self.assertEqual(Api(fresh2).post("/me/nickname/reroll").status_code, 409)


class InputTest(BaseTest):
    def test_nul_bytes_broken_unicode_and_bad_json_get_a_clean_400(self):
        user, other = make_user(), make_user()
        api = Api(user)
        cases = [
            api.post("/requests", {"to_user_id": str(other.id), "body": "Hallo\x00"}),
            api.post("/reports", {"target_type": "profile", "target_id": str(other.id), "reason": "spam", "note": "a\x00b"}),
            api.post("/me/place-changes", {"field": "home", "new_ags": "\x00"}),
            Api().post("/auth/login", {"email": "a\x00@example.org", "password": "x"}),
            api.get("/nearby/people", home="\x00"),
            Api()._wrap(Api().client.post("/api/auth/login", b'{"email": "\\ud800", "password": "x"}', content_type="application/json")),
            Api()._wrap(Api().client.post("/api/auth/login", b'{kein json', content_type="application/json")),
            Api()._wrap(Api().client.post("/api/auth/login", b"\xff\xfe", content_type="application/json")),
        ]
        for response in cases:
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["code"], "bad_request")
            self.assertEqual(response["Cache-Control"], "private, no-store")


class RegistrationHardeningTest(BaseTest):
    def test_existing_address_counts_against_the_ip_limit_like_any_other(self):
        from .test_registration import payload

        make_user(email="da@example.org")
        with self.captureOnCommitCallbacks(execute=True):
            for _ in range(3):
                self.assertEqual(Api().post("/auth/register", payload(email="da@example.org")).status_code, 202)
        self.assertEqual(RegistrationIP.objects.count(), 3)
        self.assertEqual(Api().get("/auth/challenge", purpose="register").data["maxnumber"], 400)

    def test_unverified_account_expires_after_48_hours_by_timestamp(self):
        from django.core import mail, signing

        user = make_user(status="pending", verified=False, created_at=timezone.now() - timedelta(hours=49))
        token = signing.dumps({"u": str(user.id)}, salt="verify-email")
        self.assertEqual(Api().post("/auth/verify-email", {"token": token}).status_code, 400)
        with self.captureOnCommitCallbacks(execute=True):
            Api().post("/auth/resend-verification", {"email": user.email, "pow": solved_pow()})
        self.assertEqual(mail.outbox, [])
        self.assertEqual(Api().post("/auth/login", {"email": user.email, "password": PASSWORD}).status_code, 401)


class RegistrationParallelTest(ParallelTest):
    def test_parallel_registrations_cannot_slip_under_the_ip_limit(self):
        from django.test import RequestFactory

        from accounts import services

        def register(i):
            request = RequestFactory().post("/api/auth/register", REMOTE_ADDR="10.9.8.7")
            try:
                services.register(
                    request, email=f"p{i}@example.org", password="ein-wirklich-langes-passwort",
                    birth_date=timezone.localdate().replace(year=1990), home_ags=SONTHOFEN, residence_ags=MARL,
                    invite_code=None, accept_terms=True, pow_payload=solved_pow(),
                )
                return "ok"
            finally:
                pass

        results = run_parallel([(lambda i=i: register(i)) for i in range(8)])
        self.assertEqual(kinds(results), ["ok"] * 3 + ["pow_harder_required"] * 5, results)
        self.assertEqual(User.objects.filter(email__startswith="p").count(), 3)


class LoginParallelTest(ParallelTest):
    def test_parallel_wrong_passwords_are_counted_one_after_another(self):
        user = make_user()
        barrier, codes = Barrier(12), []

        def worker():
            barrier.wait(timeout=10)
            try:
                codes.append(Api().post("/auth/login", {"email": user.email, "password": "falsch"}, REMOTE_ADDR="10.1.1.1").status_code)
            finally:
                connection.close()

        threads = [Thread(target=worker) for _ in range(12)]
        [t.start() for t in threads]
        [t.join(timeout=30) for t in threads]
        self.assertEqual(sorted(codes), [401] * 5 + [429] * 7)
        self.assertEqual(LoginFailure.objects.count(), 5)

    def test_mutual_reports_do_not_deadlock(self):
        a, b = make_user(), make_user(residence=RECKLINGHAUSEN)
        for _ in range(5):
            Report.objects.all().delete()
            results = run_parallel([
                lambda: moderation.create_report(a, target_type="profile", target_id=b.id, conversation_id=None, reason="spam", note=""),
                lambda: moderation.create_report(b, target_type="profile", target_id=a.id, conversation_id=None, reason="spam", note=""),
            ])
            self.assertEqual(kinds(results), ["ok", "ok"], results)


class LoginLockTest(BaseTest):
    def test_lock_lasts_15_minutes_from_the_latest_failure(self):
        user = make_user()
        now = timezone.now()
        hashes = dict(account_hash=account_hash(user.email), ip_hash=ip_hash("127.0.0.1"))
        LoginFailure.objects.bulk_create(
            [LoginFailure(created_at=now - timedelta(minutes=14, seconds=30), **hashes) for _ in range(4)]
            + [LoginFailure(created_at=now - timedelta(seconds=5), **hashes)]
        )
        locked = Api().post("/auth/login", {"email": user.email, "password": PASSWORD})
        self.assertEqual(locked.status_code, 429)
        self.assertGreater(locked.data["retry_after"], 14 * 60)

    def test_admin_cannot_be_locked_out_by_failures_from_elsewhere(self):
        admin = make_admin()
        LoginFailure.objects.bulk_create(
            [LoginFailure(account_hash=account_hash(admin.email), ip_hash=ip_hash(f"10.2.0.{i}")) for i in range(25)]
        )
        self.assertEqual(otp_client(admin).get(f"{ADMIN}/").status_code, 200)


class AppealRulesTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.first, self.second = make_admin(), make_admin()
        self.user = make_user()

    def test_direct_suspension_also_needs_a_second_person_and_allows_one_appeal(self):
        with self.captureOnCommitCallbacks(execute=True):
            moderation.suspend(self.first, self.user, "direkt")
        token = moderation.appeal_link(self.user).split("token=")[1]
        self.assertEqual(Api().post("/appeals/by-token", {"token": token, "text": "Bitte prüfen"}).status_code, 201)
        self.assertEqual(Api().post("/appeals/by-token", {"token": token, "text": "Nochmal"}).status_code, 409)
        appeal = Appeal.objects.get()
        with self.assertRaises(PermissionError):
            moderation.decide_appeal(self.first, appeal, overturned=False)
        with self.captureOnCommitCallbacks(execute=True):
            moderation.decide_appeal(self.second, appeal, overturned=True)
        # Eine spätere, neue Sperre kann wieder angefochten werden.
        self.user.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            moderation.suspend(self.second, self.user, "erneut")
        self.assertEqual(Api().post("/appeals/by-token", {"token": token, "text": "Neue Sperre"}).status_code, 201)

    def test_appeals_without_report_are_cleaned_up_too(self):
        Appeal.objects.create(user=self.user, text="alt", decided_at=timezone.now() - timedelta(days=400), outcome="upheld")
        cleanup.run()
        self.assertEqual(Appeal.objects.count(), 0)

    def test_dismissal_and_unmute_are_not_undone_by_the_next_report(self):
        target = make_user(residence=RECKLINGHAUSEN)
        for _ in range(3):
            Api(make_user()).post("/reports", {"target_type": "profile", "target_id": str(target.id), "reason": "spam"})
        target.refresh_from_db()
        self.assertIsNotNone(target.muted_until)
        moderation.resolve_incident(self.first, Report.objects.first().incident_key, confirmed=False)
        moderation.unmute(self.first, target, "abgesprochene Meldungen")
        Api(make_user()).post("/reports", {"target_type": "profile", "target_id": str(target.id), "reason": "spam"})
        target.refresh_from_db()
        self.assertIsNone(target.muted_until)
        # Die neue Meldung gehört nicht zum bereits geschlossenen Vorfall.
        self.assertEqual(Report.objects.values("incident_key").distinct().count(), 2)


class AdminQueueTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.admin = make_admin()
        self.client = otp_client(self.admin)

    def test_open_reports_come_before_resolved_ones(self):
        a, b = make_user(), make_user()
        Api(make_user()).post("/reports", {"target_type": "profile", "target_id": str(a.id), "reason": "other"})
        moderation.resolve_incident(self.admin, Report.objects.get().incident_key, confirmed=False)
        Api(make_user()).post("/reports", {"target_type": "profile", "target_id": str(b.id), "reason": "harassment"})
        content = self.client.get(f"{ADMIN}/moderation/report/").content.decode()
        self.assertLess(content.index("Belästigung"), content.index("Sonstiges"))

    def test_approval_queue_shows_the_oldest_first(self):
        young = make_user(status="pending", approval_required=True, created_at=timezone.now() - timedelta(days=1))
        old = make_user(status="pending", approval_required=True, created_at=timezone.now() - timedelta(days=20))
        content = self.client.get(f"{ADMIN}/accounts/user/?zustand=freigabe").content.decode()
        self.assertLess(content.index(old.nickname), content.index(young.nickname))

    def test_role_changes_are_audited_and_need_an_account_without_places(self):
        ordinary = make_user()
        response = self.client.post(f"{ADMIN}/accounts/moderator/add/", {"user": str(ordinary.id), "role": "admin"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Moderator.objects.filter(user=ordinary).exists())
        staff = make_user(home=None, residence=None)
        self.assertEqual(self.client.post(f"{ADMIN}/accounts/moderator/add/", {"user": str(staff.id), "role": "moderator"}).status_code, 302)
        self.assertTrue(AuditLog.objects.filter(action="moderator_created", target_user=staff).exists())

    def test_moderators_do_not_see_email_or_birth_year(self):
        user = make_user()
        client = otp_client(make_admin(role="moderator"))
        page = client.get(f"{ADMIN}/accounts/user/{user.id}/change/").content.decode()
        self.assertNotIn(user.email, page)
        self.assertNotIn("Geburtsjahr", page)
        self.assertNotIn(user.nickname, client.get(f"{ADMIN}/accounts/user/?q={user.email}").content.decode())
        self.assertIn(user.email, self.client.get(f"{ADMIN}/accounts/user/{user.id}/change/").content.decode())


class TombstoneTest(BaseTest):
    def test_tombstone_keeps_only_id_status_and_deleted_at(self):
        staff = make_admin()
        delete_account(staff.id)
        row = User.objects.filter(pk=staff.pk).values().get()
        kept = {k for k, v in row.items() if v not in (None, False, 0, "")}
        self.assertEqual(kept, {"id", "status", "deleted_at", "session_epoch"})
        self.assertFalse(Moderator.objects.filter(user_id=staff.pk).exists())
