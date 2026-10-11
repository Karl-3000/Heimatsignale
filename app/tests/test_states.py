"""Zustandsmatrix aus PROJEKT.md, Abschnitt 6: jede Zelle wird geprüft."""

from datetime import timedelta

from django.utils import timezone

from accounts import states
from accounts.models import User
from contacts import services as contacts

from .base import PASSWORD, RECKLINGHAUSEN, Api, BaseTest, make_user


def in_state(state: str) -> User:
    now = timezone.now()
    if state == states.UNVERIFIED:
        return make_user(status="pending", verified=False, residence=RECKLINGHAUSEN)
    if state == states.AWAITING_APPROVAL:
        return make_user(status="pending", approval_required=True, residence=RECKLINGHAUSEN)
    if state == states.ACTIVE:
        return make_user(residence=RECKLINGHAUSEN)
    if state == states.MUTED:
        return make_user(residence=RECKLINGHAUSEN, muted_until=now + timedelta(hours=1))
    if state == states.SUSPENDED:
        return make_user(status="suspended", residence=RECKLINGHAUSEN)
    raise ValueError(state)


class EffectiveStateTest(BaseTest):
    def test_state_is_computed_from_attributes_and_time(self):
        for state in (states.UNVERIFIED, states.AWAITING_APPROVAL, states.ACTIVE, states.MUTED, states.SUSPENDED):
            self.assertEqual(states.effective_state(in_state(state)), state)

    def test_mute_ends_by_timestamp_without_any_job(self):
        user = make_user(muted_until=timezone.now() + timedelta(seconds=30))
        self.assertEqual(states.effective_state(user), states.MUTED)
        later = timezone.now() + timedelta(seconds=31)
        self.assertEqual(states.effective_state(user, later), states.ACTIVE)

    def test_activation_needs_all_required_approvals(self):
        user = make_user(status="pending", verified=False, approval_required=True)
        self.assertFalse(states.apply_activation(user))
        user.email_verified_at = timezone.now()
        self.assertFalse(states.apply_activation(user))
        user.approved_at = timezone.now()
        self.assertTrue(states.apply_activation(user))
        self.assertEqual(user.status, "active")


class PermissionMatrixTest(BaseTest):
    STATES = (states.UNVERIFIED, states.AWAITING_APPROVAL, states.ACTIVE, states.MUTED, states.SUSPENDED)

    def setUp(self):
        super().setUp()
        self.viewer = make_user()

    def test_login(self):
        expected = {states.UNVERIFIED: 403, states.AWAITING_APPROVAL: 200, states.ACTIVE: 200, states.MUTED: 200,
                    states.SUSPENDED: 403}
        for state in self.STATES:
            user = in_state(state)
            response = Api().post("/auth/login", {"email": user.email, "password": PASSWORD})
            self.assertEqual(response.status_code, expected[state], state)

    def test_awaiting_approval_sees_only_the_status_page(self):
        api = Api(in_state(states.AWAITING_APPROVAL))
        self.assertEqual(api.get("/session").data["state"], "awaiting_approval")
        for path in ("/nearby/overview", "/requests", "/conversations", "/blocks"):
            response = api.get(path)
            self.assertEqual((response.status_code, response.data["code"]), (403, "awaiting_approval"), path)

    def test_existing_session_ends_when_account_is_suspended(self):
        user = in_state(states.ACTIVE)
        api = Api(user)
        self.assertEqual(api.get("/requests").status_code, 200)
        User.objects.filter(pk=user.pk).update(status="suspended")
        self.assertEqual(api.get("/requests").status_code, 401)
        self.assertFalse(api.get("/session").data["authenticated"])

    def test_visible_and_counted(self):
        visible = {states.ACTIVE, states.MUTED}
        for state in self.STATES:
            user = in_state(state)
            api = Api(self.viewer)
            total = api.get("/nearby/overview").data["total"]
            profile = api.get(f"/users/{user.id}")
            self.assertEqual(profile.status_code, 200 if state in visible else 404, state)
            self.assertEqual(total, 1 if state in visible else 0, state)
            User.objects.filter(pk=user.pk).delete()

    def test_send_requests(self):
        target = make_user(residence=RECKLINGHAUSEN)
        expected = {states.ACTIVE: 201, states.MUTED: 403}
        for state, status in expected.items():
            response = Api(in_state(state)).post("/requests", {"to_user_id": str(target.id), "body": "Hallo aus der Heimat"})
            self.assertEqual(response.status_code, status, state)
        self.assertEqual(response.data["code"], "muted")

    def test_receive_requests(self):
        receivable = {states.ACTIVE, states.MUTED}
        for state in self.STATES:
            user = in_state(state)
            response = Api(self.viewer).post("/requests", {"to_user_id": str(user.id), "body": "Hallo aus der Heimat"})
            self.assertEqual(response.status_code, 201 if state in receivable else 404, state)

    def test_muted_user_can_accept_and_keeps_conversations(self):
        muted = in_state(states.MUTED)
        result = contacts.send_request(self.viewer, muted.id, "Hallo")
        api = Api(muted)
        accepted = api.post(f"/requests/{result['request_id']}/accept")
        self.assertEqual(accepted.status_code, 200)
        sent = api.post(f"/conversations/{accepted.data['conversation_id']}/messages", {"body": "Schön, von dir zu lesen"})
        self.assertEqual(sent.status_code, 201)

    def test_conversation_unavailable_while_partner_is_suspended(self):
        other = in_state(states.ACTIVE)
        result = contacts.send_request(self.viewer, other.id, "Hallo")
        conv = contacts.accept_request(other, result["request_id"])
        User.objects.filter(pk=other.pk).update(status="suspended")
        api = Api(self.viewer)
        self.assertFalse(api.get(f"/conversations/{conv.id}/messages").data["available"])
        self.assertEqual(api.post(f"/conversations/{conv.id}/messages", {"body": "Noch da?"}).status_code, 403)
        self.assertIsNone(api.get("/conversations").data["items"][0]["partner"])

    def test_appeal_only_while_muted(self):
        self.assertEqual(Api(in_state(states.ACTIVE)).post("/appeals", {"text": "Bitte prüfen"}).status_code, 400)
        self.assertEqual(Api(in_state(states.MUTED)).post("/appeals", {"text": "Bitte prüfen"}).status_code, 201)
