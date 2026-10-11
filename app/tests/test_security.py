import json

from django.conf import settings
from django.test import Client

from accounts.models import User

from .base import MUENSTER, PASSWORD, Api, BaseTest, make_user


class CsrfTest(BaseTest):
    """Zustandsändernde Aufrufe brauchen den CSRF-Token im Header (Abschnitt 11)."""

    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.other = make_user()

    def test_login_without_token_fails_and_with_token_works(self):
        client = Client(enforce_csrf_checks=True)
        body = json.dumps({"email": self.user.email, "password": PASSWORD})
        denied = client.post("/api/auth/login", body, content_type="application/json")
        self.assertEqual((denied.status_code, denied.json()["code"]), (403, "csrf_failed"))
        token = client.get("/api/session").json()["csrf_token"]
        ok = client.post("/api/auth/login", body, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(ok.status_code, 200)

    def test_every_state_changing_endpoint_fails_without_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user, backend="accounts.backends.ThrottledBackend")
        calls = [
            ("post", "/api/requests", {"to_user_id": str(self.other.id), "body": "Hallo"}),
            ("post", "/api/blocks", {"user_id": str(self.other.id)}),
            ("post", "/api/reports", {"target_type": "profile", "target_id": str(self.other.id), "reason": "spam"}),
            ("post", "/api/me/delete", {"password": PASSWORD}),
            ("post", "/api/auth/logout", {}),
            ("delete", f"/api/blocks/{self.other.id}", None),
            ("post", "/api/places/nearest", {"lat": 51.6, "lon": 7.1}),
        ]
        for method, path, data in calls:
            kwargs = {"content_type": "application/json"}
            response = getattr(client, method)(path, json.dumps(data) if data is not None else "", **kwargs)
            self.assertEqual(response.status_code, 403, path)
            self.assertEqual(response.json()["code"], "csrf_failed", path)
        self.assertEqual(User.objects.get(pk=self.user.pk).status, "active")
        # Mit Token geht derselbe Aufruf durch.
        token = client.get("/api/session").json()["csrf_token"]
        ok = client.post("/api/blocks", json.dumps({"user_id": str(self.other.id)}), content_type="application/json",
                         HTTP_X_CSRFTOKEN=token)
        self.assertEqual(ok.status_code, 204)

    def test_a_token_from_another_session_does_not_work(self):
        foreign = Client(enforce_csrf_checks=True).get("/api/session").json()["csrf_token"]
        client = Client(enforce_csrf_checks=True)
        response = client.post("/api/auth/logout", "", content_type="application/json", HTTP_X_CSRFTOKEN=foreign)
        self.assertEqual(response.status_code, 403)


class HeadersAndAccessTest(BaseTest):
    def test_api_responses_are_never_cached(self):
        user = make_user()
        for response in (Api().get("/session"), Api(user).get("/nearby/overview"), Api().get("/requests"),
                         Api().get("/places/search", q="marl"), Api(user).get("/gibt-es-nicht")):
            self.assertEqual(response["Cache-Control"], "private, no-store", response.request["PATH_INFO"])

    def test_cookie_flags(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY and settings.CSRF_COOKIE_HTTPONLY)
        self.assertEqual((settings.SESSION_COOKIE_SAMESITE, settings.CSRF_COOKIE_SAMESITE), ("Lax", "Lax"))
        response = Api().post("/auth/login", {"email": make_user().email, "password": PASSWORD})
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    def test_production_settings_require_secure_cookies(self):
        import importlib
        import os
        from unittest import mock

        from heimatsignale import settings as module

        with mock.patch.dict(os.environ, {"DEBUG": "0", "SECRET_KEY": "x" * 50}):
            production = importlib.reload(module)
            flags = (production.SESSION_COOKIE_SECURE, production.CSRF_COOKIE_SECURE, production.SECURE_HSTS_SECONDS > 0)
        importlib.reload(module)
        self.assertEqual(flags, (True, True, True))

    def test_everything_about_users_needs_a_login(self):
        target = make_user()
        api = Api()
        paths = ["/nearby/overview", "/nearby/origins", "/nearby/people?home=09780139", f"/users/{target.id}",
                 "/requests", "/conversations", "/blocks", "/inbox/summary", "/me/place-changes"]
        for path in paths:
            response = api.get(path)
            self.assertEqual((response.status_code, response.data["code"]), (401, "not_authenticated"), path)

    def test_there_is_no_user_write_api_for_home_or_residence(self):
        user = make_user()
        api = Api(user)
        for method, path in (("post", "/me"), ("post", "/me/residence"), ("post", "/me/home"), ("post", f"/users/{user.id}")):
            self.assertIn(getattr(api, method)(path, {"residence_ags": MUENSTER, "home_ags": MUENSTER}).status_code, (404, 405), path)
        # Der einzige Weg ist der Antrag; bis zur Entscheidung bleibt der alte Wert aktiv.
        created = api.post("/me/place-changes", {"field": "residence", "new_ags": MUENSTER})
        self.assertEqual((created.status_code, created.data["decision"]), (201, None))
        self.assertEqual(api.post("/me/place-changes", {"field": "residence", "new_ags": MUENSTER}).data["code"], "change_pending")
        user.refresh_from_db()
        self.assertNotEqual(user.residence_id, MUENSTER)
        self.assertEqual(api.get("/session").data["user"]["residence"]["name"], "Marl")

    def test_profile_shows_only_the_allowed_fields(self):
        viewer, target = make_user(), make_user(birth_year=1990)
        data = Api(viewer).get(f"/users/{target.id}").data
        self.assertEqual(set(data["user"]), {"id", "nickname", "age_range", "home", "residence", "member_since"})
        self.assertEqual(set(data["user"]["home"]), {"ags", "name", "district_ags", "district_name", "state_code", "state_name"})
        self.assertRegex(data["user"]["age_range"], r"^\d\d–\d\d$|^65\+$")
        self.assertRegex(data["user"]["member_since"], r"^\d{4}-\d{2}$")

    def test_age_range_comes_from_the_calendar_year(self):
        from datetime import date

        from accounts.services import age_range

        self.assertEqual(age_range(2001, date(2026, 1, 1)), "25–34")
        self.assertEqual(age_range(2002, date(2026, 12, 31)), "18–24")
        self.assertEqual(age_range(1961, date(2026, 6, 1)), "65+")

    def test_data_model_has_none_of_the_excluded_fields(self):
        names = {f.name for f in User._meta.get_fields()}
        for forbidden in ("gender", "sex", "photo", "avatar", "bio", "about", "hobbies", "interests", "birth_date",
                          "latitude", "longitude", "lat", "lon", "last_login", "online", "first_name", "last_name"):
            self.assertNotIn(forbidden, names)
