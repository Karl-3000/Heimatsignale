from datetime import date, timedelta
from threading import Barrier, Thread

from django.core import mail
from django.db import connection
from django.utils import timezone

from accounts import nicknames, services
from accounts.models import InviteCode, RegistrationIP, User
from accounts.net import ip_hash
from jobs import cleanup

from .base import MARL, SONTHOFEN, Api, BaseTest, ParallelTest, make_user, solved_pow


def payload(**over):
    data = {
        "email": "neu@example.org", "password": "ein-wirklich-langes-passwort", "birth_date": "1994-03-17",
        "home_ags": SONTHOFEN, "residence_ags": MARL, "invite_code": None, "accept_terms": True, "pow": solved_pow(),
    }
    data.update(over)
    return data


def token_from_mail() -> str:
    return mail.outbox[-1].body.split("token=")[1].split()[0]


class RegistrationTest(BaseTest):
    def register(self, **over):
        with self.captureOnCommitCallbacks(execute=True):
            return Api().post("/auth/register", payload(**over))

    def test_full_flow_stores_only_birth_year(self):
        self.assertEqual(self.register().status_code, 202)
        user = User.objects.get(email="neu@example.org")
        self.assertEqual((user.status, user.birth_year, user.adult_self_declared_at), ("pending", 1994, timezone.localdate()))
        self.assertTrue(nicknames.is_allowed(user.nickname))
        self.assertFalse(hasattr(user, "birth_date"))

        api = Api()
        self.assertEqual(api.post("/auth/login", {"email": user.email, "password": payload()["password"]}).data["code"], "unverified")
        verified = api.post("/auth/verify-email", {"token": token_from_mail()})
        self.assertEqual((verified.status_code, verified.data["state"]), (200, "active"))
        self.assertEqual(verified.data["user"]["home"]["name"], "Sonthofen")
        self.assertEqual(api.post("/auth/verify-email", {"token": token_from_mail()}).status_code, 400)

    def test_nickname_can_be_rerolled_exactly_once(self):
        self.register()
        api = Api()
        first = api.post("/auth/verify-email", {"token": token_from_mail()}).data["user"]["nickname"]
        rerolled = api.post("/me/nickname/reroll")
        self.assertEqual(rerolled.data["nickname_rerolls_left"], 0)
        self.assertNotEqual(rerolled.data["nickname"], first)
        self.assertEqual(api.post("/me/nickname/reroll").data["code"], "reroll_used")

    def test_validation(self):
        today = timezone.localdate()
        almost_18 = date(today.year - 18, today.month, today.day) + timedelta(days=1)
        cases = {
            "birth_date": {"birth_date": almost_18.isoformat()},
            "email": {"email": "jemand@mailinator.com"},
            "password": {"password": "zu-kurz"},
            "home_ags": {"home_ags": "00000000"},
            "residence_ags": {"residence_ags": "Paris"},
            "accept_terms": {"accept_terms": False},
            "invite_code": {"invite_code": "GIBT-ES-NICHT"},
        }
        for field, over in cases.items():
            response = self.register(**over)
            self.assertEqual(response.status_code, 422, field)
            self.assertIn(field, response.data["fields"], field)
        self.assertEqual(User.objects.count(), 0)

    def test_exactly_18_today_is_allowed(self):
        today = timezone.localdate()
        self.assertTrue(services.is_adult(date(today.year - 18, today.month, today.day), today))
        self.assertFalse(services.is_adult(date(today.year - 18, 12, 31), date(today.year, 12, 30)))

    def test_existing_email_gets_same_answer_and_no_second_account(self):
        existing = make_user(email="neu@example.org")
        response = self.register()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(User.objects.filter(email="neu@example.org").count(), 1)
        self.assertIn("bereits ein Konto", mail.outbox[-1].body)
        self.assertEqual(mail.outbox[-1].to, [existing.email])

    def test_pow_is_required_and_single_use(self):
        self.assertEqual(self.register(pow=None).data["code"], "pow_invalid")
        solved = solved_pow()
        self.assertEqual(self.register(pow=solved).status_code, 202)
        self.assertEqual(self.register(pow=solved, email="zwei@example.org").data["code"], "pow_invalid")

    def test_ip_limit_is_graduated_not_a_hard_block(self):
        for i in range(3):
            self.assertEqual(self.register(email=f"a{i}@example.org").status_code, 202)
        self.assertFalse(User.objects.filter(approval_required=True).exists())
        # Vierte Registrierung in 24 Stunden: schwerere Aufgabe und Admin-Freigabe.
        self.assertEqual(self.register(email="a3@example.org").data["code"], "pow_harder_required")
        challenge = Api().get("/auth/challenge", purpose="register").data
        self.assertEqual(challenge["maxnumber"], 400)
        self.assertEqual(self.register(email="a3@example.org", pow=solved_pow(hard=True)).status_code, 202)
        user = User.objects.get(email="a3@example.org")
        self.assertTrue(user.approval_required)

        api = Api()
        state = api.post("/auth/verify-email", {"token": token_from_mail()}).data["state"]
        self.assertEqual(state, "awaiting_approval")
        self.assertEqual(api.get("/nearby/overview").data["code"], "awaiting_approval")

    def test_seven_day_limit(self):
        RegistrationIP.objects.bulk_create(
            [RegistrationIP(ip_hash=ip_hash("127.0.0.1"), created_at=timezone.now() - timedelta(days=3)) for _ in range(10)]
        )
        self.assertTrue(services.ip_over_limit("127.0.0.1"))
        RegistrationIP.objects.update(created_at=timezone.now() - timedelta(days=8))
        self.assertFalse(services.ip_over_limit("127.0.0.1"))

    def test_invite_code_bypasses_ip_limit_and_is_counted(self):
        code = InviteCode.objects.create(label="Neubürgerabend", valid_until=timezone.now() + timedelta(days=1), max_uses=2)
        for i in range(3):
            self.register(email=f"a{i}@example.org")
        self.assertEqual(self.register(email="gast1@example.org", invite_code=code.code).status_code, 202)
        self.assertFalse(User.objects.get(email="gast1@example.org").approval_required)
        self.assertEqual(self.register(email="gast2@example.org", invite_code=code.code.lower()).status_code, 202)
        self.assertIn("invite_code", self.register(email="gast3@example.org", invite_code=code.code).data["fields"])
        code.refresh_from_db()
        self.assertEqual(code.used_count, 2)
        self.assertEqual(RegistrationIP.objects.filter(invite_code=code).count(), 2)

    def test_unverified_accounts_go_after_48_hours_but_the_approval_queue_stays(self):
        old = timezone.now() - timedelta(hours=49)
        unverified_old = make_user(status="pending", verified=False, created_at=old)
        unverified_new = make_user(status="pending", verified=False, created_at=timezone.now() - timedelta(hours=47))
        queued = make_user(status="pending", approval_required=True, created_at=timezone.now() - timedelta(days=20))
        with self.captureOnCommitCallbacks(execute=True):
            result = cleanup.run()
        ids = set(User.objects.values_list("id", flat=True))
        self.assertNotIn(unverified_old.id, ids)
        self.assertLessEqual({unverified_new.id, queued.id}, ids)
        # Nach 14 Tagen gibt es genau einmal eine E-Mail mit dem Stand.
        self.assertEqual(result["approval_notices"], 1)
        self.assertEqual(mail.outbox[-1].to, [queued.email])
        self.assertEqual(cleanup.run()["approval_notices"], 0)

    def test_nicknames_follow_format_and_blocklist(self):
        for _ in range(500):
            self.assertTrue(nicknames.is_allowed(nicknames.generate()))
        for bad in ("Stiller-Kranich-88", "Stiller-Kranich-188", "stiller-kranich-12", "Stiller Kranich 12", "Flirt-Kranich-12"):
            self.assertFalse(nicknames.is_allowed(bad), bad)

    def test_database_rejects_free_nicknames(self):
        from django.db import IntegrityError, transaction

        user = make_user()
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=user.pk).update(nickname="SexyHexy99")

    def test_password_reset(self):
        user = make_user()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(Api().post("/auth/password-reset", {"email": user.email, "pow": solved_pow()}).status_code, 202)
            self.assertEqual(Api().post("/auth/password-reset", {"email": "nie@example.org", "pow": solved_pow()}).status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        link = mail.outbox[0].body.split("passwort-neu?")[1].split()[0]
        params = dict(p.split("=", 1) for p in link.split("&"))
        new = "ein-ganz-neues-langes-passwort"
        self.assertEqual(Api().post("/auth/password-reset/confirm", {**params, "password": "kurz"}).status_code, 422)
        self.assertEqual(Api().post("/auth/password-reset/confirm", {**params, "password": new}).status_code, 204)
        self.assertEqual(Api().post("/auth/password-reset/confirm", {**params, "password": new + "x"}).status_code, 400)
        self.assertEqual(Api().post("/auth/login", {"email": user.email, "password": new}).status_code, 200)


class InviteCodeParallelTest(ParallelTest):
    def test_last_use_is_given_out_exactly_once(self):
        code = InviteCode.objects.create(label="Fest", valid_until=timezone.now() + timedelta(days=1), max_uses=1)
        barrier, results = Barrier(8), []

        def worker():
            barrier.wait()
            try:
                results.append(services.consume_invite(code.id))
            finally:
                connection.close()

        threads = [Thread(target=worker) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(results.count(True), 1)
        code.refresh_from_db()
        self.assertEqual(code.used_count, 1)
