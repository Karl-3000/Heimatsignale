from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from accounts.models import LoginFailure
from accounts.net import account_hash, ip_hash

from .base import PASSWORD, Api, BaseTest, make_user, solved_pow


class LoginRulesTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.user = make_user()

    def login(self, password=PASSWORD, ip="127.0.0.1", pow=None, email=None):
        return Api().post("/auth/login", {"email": email or self.user.email, "password": password, "pow": pow}, REMOTE_ADDR=ip)

    def test_five_failures_lock_account_and_ip_for_15_minutes(self):
        for _ in range(5):
            self.assertEqual(self.login("falsch").status_code, 401)
        locked = self.login()
        self.assertEqual((locked.status_code, locked.data["code"]), (429, "login_locked"))
        self.assertLessEqual(locked.data["retry_after"], 15 * 60 + 1)
        # Dieselbe Person von einer anderen IP ist nicht gesperrt.
        self.assertEqual(self.login(ip="10.0.0.9").status_code, 200)
        # Nach 15 Minuten endet die Sperre von selbst.
        LoginFailure.objects.update(created_at=timezone.now() - timedelta(minutes=16))
        self.assertEqual(self.login().status_code, 200)

    def test_unknown_email_behaves_like_wrong_password(self):
        response = self.login(email="gibt-es-nicht@example.org")
        self.assertEqual((response.status_code, response.data["code"]), (401, "invalid_credentials"))

    def test_twenty_failures_across_ips_require_pow_but_never_lock(self):
        LoginFailure.objects.bulk_create(
            [LoginFailure(account_hash=account_hash(self.user.email), ip_hash=ip_hash(f"10.1.0.{i}")) for i in range(20)]
        )
        self.assertEqual(self.login().data["code"], "pow_required")
        self.assertEqual(self.login(pow=solved_pow()).status_code, 200)

    @override_settings(LOGIN_IP_FAILURES=6)
    def test_ip_wide_lock_after_many_failures(self):
        for i in range(6):
            self.login("falsch", email=f"opfer{i}@example.org")
        self.assertEqual(self.login().data["code"], "login_locked")
        self.assertEqual(self.login(ip="10.0.0.9").status_code, 200)

    def test_success_clears_the_pair_counter(self):
        for _ in range(4):
            self.login("falsch")
        self.assertEqual(self.login().status_code, 200)
        for _ in range(4):
            self.login("falsch")
        self.assertEqual(self.login().status_code, 200)

    def test_staff_accounts_use_the_admin_area(self):
        from .base import make_admin

        admin = make_admin()
        self.assertEqual(self.login(email=admin.email).data["code"], "staff_only_admin")
