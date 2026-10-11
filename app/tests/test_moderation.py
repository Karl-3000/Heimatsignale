from datetime import timedelta

from django.core import mail
from django.utils import timezone

from accounts import states
from accounts.models import User
from contacts import services as contacts
from contacts.models import Message
from jobs import cleanup
from moderation import services as moderation
from moderation.models import Appeal, Report

from .base import MUENSTER, RECKLINGHAUSEN, Api, BaseTest, make_admin, make_user


class ReportTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.a, self.b = make_user(), make_user(residence=RECKLINGHAUSEN)
        request_id = contacts.send_request(self.b, self.a.id, "Hallo")["request_id"]
        self.conv = contacts.accept_request(self.a, request_id)
        self.api_a = Api(self.a)

    def report(self, api=None, **over):
        data = {"target_type": "profile", "target_id": str(self.b.id), "reason": "dating", "note": "Aufdringlich"}
        data.update(over)
        return (api or self.api_a).post("/reports", data)

    def test_message_report_copies_the_text_and_up_to_ten_previous_messages(self):
        start = timezone.now()
        for i in range(14):
            Message.objects.create(conversation=self.conv, sender=self.b if i % 2 else self.a, body=f"Text {i}",
                                   created_at=start + timedelta(seconds=i + 1))
        target = Message.objects.create(conversation=self.conv, sender=self.b, body="Lust auf ein Date?",
                                        created_at=start + timedelta(seconds=30))
        response = self.report(target_type="message", target_id=str(target.id), conversation_id=str(self.conv.id))
        self.assertEqual(response.status_code, 201)
        report = Report.objects.get()
        self.assertEqual((report.reported_user_id, report.reporter_id), (self.b.id, self.a.id))
        self.assertEqual(report.snapshot["text"], "Lust auf ein Date?")
        self.assertEqual([c["text"] for c in report.snapshot["context"]], [f"Text {i}" for i in range(4, 14)])
        self.assertEqual({c["from"] for c in report.snapshot["context"]}, {"meldende Person", "gemeldete Person"})
        # Der Schnappschuss ist eine Kopie: Löschen der Nachricht ändert ihn nicht.
        target.delete()
        self.assertEqual(Report.objects.get().snapshot["text"], "Lust auf ein Date?")

    def test_snapshot_only_secures_what_still_exists(self):
        gone = Message.objects.create(conversation=self.conv, sender=self.b, body="schnell gelöscht")
        gone_id = gone.id
        gone.delete()
        self.report(target_type="message", target_id=str(gone_id), conversation_id=str(self.conv.id))
        report = Report.objects.get()
        self.assertEqual(report.snapshot, {"kind": "message", "deleted": True, "text": "Inhalt vom Absender gelöscht"})
        self.assertEqual(report.note, "Aufdringlich")

    def test_request_report(self):
        c = make_user(residence=RECKLINGHAUSEN)
        request_id = contacts.send_request(c, self.a.id, "Na du, Single?")["request_id"]
        self.assertEqual(self.report(target_type="request", target_id=request_id).status_code, 201)
        report = Report.objects.get()
        self.assertEqual((report.reported_user_id, report.snapshot["text"]), (c.id, "Na du, Single?"))

    def test_only_accessible_targets_can_be_reported(self):
        far = make_user(residence=MUENSTER)
        self.assertEqual(self.report(target_id=str(far.id)).status_code, 404)
        stranger = Api(make_user(residence=MUENSTER))
        own = Message.objects.filter(sender=self.b).first()
        self.assertEqual(self.report(api=stranger, target_type="message", target_id=str(own.id),
                                     conversation_id=str(self.conv.id)).status_code, 404)
        self.assertEqual(self.report(reason="langweilig").status_code, 422)
        self.assertEqual(Report.objects.count(), 0)

    def test_reporting_is_possible_after_blocking(self):
        self.api_a.post("/blocks", {"user_id": str(self.b.id)})
        self.assertEqual(self.report().status_code, 201)

    def test_reports_on_the_same_target_within_7_days_form_one_incident(self):
        c = make_user()
        self.report()
        self.report()  # dieselbe Person noch einmal: zusammengeführt
        self.report(api=Api(c))
        self.assertEqual(Report.objects.count(), 2)
        self.assertEqual(Report.objects.values("incident_key").distinct().count(), 1)
        Report.objects.update(created_at=timezone.now() - timedelta(days=8))
        self.report(api=Api(make_user()))
        self.assertEqual(Report.objects.values("incident_key").distinct().count(), 2)

    def test_moderators_see_the_snapshot_not_the_mailbox(self):
        self.report()
        self.assertEqual(Report.objects.get().snapshot, {"kind": "profile", "nickname": self.b.nickname})


class AutoMuteTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.target = make_user(residence=RECKLINGHAUSEN)

    def report_from(self, user):
        return Api(user).post("/reports", {"target_type": "profile", "target_id": str(self.target.id), "reason": "spam"})

    def test_three_different_established_accounts_mute_for_48_hours(self):
        for _ in range(2):
            self.report_from(make_user())
        self.target.refresh_from_db()
        self.assertIsNone(self.target.muted_until)
        self.report_from(make_user())
        self.target.refresh_from_db()
        remaining = self.target.muted_until - timezone.now()
        self.assertTrue(timedelta(hours=47, minutes=59) < remaining <= timedelta(hours=48))
        self.assertEqual(states.effective_state(self.target), states.MUTED)
        # Die Stummschaltung endet von selbst, ohne Job und ohne Admin.
        self.assertEqual(states.effective_state(self.target, timezone.now() + timedelta(hours=48, seconds=1)), states.ACTIVE)
        self.assertEqual(self.target.status, "active")

    def test_young_accounts_do_not_count(self):
        for _ in range(2):
            self.report_from(make_user())
        for _ in range(3):
            self.report_from(make_user(active_days=6))
        self.target.refresh_from_db()
        self.assertIsNone(self.target.muted_until)

    def test_same_account_three_times_does_not_count(self):
        user = make_user()
        other = make_user(residence=RECKLINGHAUSEN)
        for target_type, target in (("profile", self.target),):
            for _ in range(3):
                Api(user).post("/reports", {"target_type": target_type, "target_id": str(target.id), "reason": "spam"})
        self.report_from(other)
        self.target.refresh_from_db()
        self.assertIsNone(self.target.muted_until)

    def test_reports_older_than_24_hours_do_not_count(self):
        for _ in range(2):
            self.report_from(make_user())
        Report.objects.update(created_at=timezone.now() - timedelta(hours=25))
        self.report_from(make_user())
        self.target.refresh_from_db()
        self.assertIsNone(self.target.muted_until)

    def test_muted_user_cannot_send_but_stays_visible_and_can_appeal_once(self):
        for _ in range(3):
            self.report_from(make_user())
        viewer = make_user()
        api = Api(self.target)
        session = api.get("/session").data
        self.assertEqual((session["state"], session["user"]["muted_until"] is not None), ("muted", True))
        self.assertEqual(api.post("/requests", {"to_user_id": str(viewer.id), "body": "Hallo"}).data["code"], "muted")
        self.assertEqual(Api(viewer).get(f"/users/{self.target.id}").status_code, 200)
        self.assertEqual(api.post("/appeals", {"text": "Das war abgesprochen."}).status_code, 201)
        self.assertEqual(api.post("/appeals", {"text": "Noch einmal."}).data["code"], "appeal_exists")


class SuspensionAndAppealTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.first, self.second = make_admin(), make_admin()
        self.target = make_user(residence=RECKLINGHAUSEN)
        self.reporter = make_user()
        Api(self.reporter).post("/reports", {"target_type": "profile", "target_id": str(self.target.id), "reason": "harassment"})
        self.report = Report.objects.get()

    def confirm(self):
        with self.captureOnCommitCallbacks(execute=True):
            moderation.resolve_incident(self.first, self.report.incident_key, confirmed=True, reason="Belege eindeutig")

    def test_confirmed_incident_suspends_and_offers_one_appeal_to_a_second_person(self):
        api = Api(self.target)
        self.confirm()
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, "suspended")
        self.assertEqual(api.get("/requests").status_code, 401)  # Sitzung beendet
        self.assertEqual(Api(self.reporter).get(f"/users/{self.target.id}").status_code, 404)

        token = mail.outbox[-1].body.split("token=")[1].split()[0]
        self.assertEqual(Api().post("/appeals/by-token", {"token": token, "text": "Das stimmt so nicht."}).status_code, 201)
        self.assertEqual(Api().post("/appeals/by-token", {"token": token, "text": "Nochmal."}).data["code"], "appeal_exists")
        self.assertEqual(Api().post("/appeals/by-token", {"token": "falsch", "text": "x"}).status_code, 400)

        appeal = Appeal.objects.get()
        with self.assertRaises(PermissionError):
            moderation.decide_appeal(self.first, appeal, overturned=True)
        with self.captureOnCommitCallbacks(execute=True):
            moderation.decide_appeal(self.second, appeal, overturned=True)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, "active")
        with self.assertRaises(ValueError):
            moderation.decide_appeal(self.second, Appeal.objects.get(), overturned=False)

    def test_dismissed_incident_changes_nothing_for_the_user(self):
        moderation.resolve_incident(self.first, self.report.incident_key, confirmed=False)
        self.target.refresh_from_db()
        self.report.refresh_from_db()
        self.assertEqual((self.target.status, self.report.outcome), ("active", "dismissed"))

    def test_review_can_still_suspend_after_the_mute_has_ended(self):
        User.objects.filter(pk=self.target.pk).update(muted_until=timezone.now() - timedelta(hours=30))
        self.confirm()
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, "suspended")

    def test_resolved_reports_and_their_appeals_are_deleted_after_12_months(self):
        self.confirm()
        Appeal.objects.create(user=self.target, report=self.report, text="Einspruch")
        Report.objects.update(resolved_at=timezone.now() - timedelta(days=364))
        cleanup.run()
        self.assertEqual((Report.objects.count(), Appeal.objects.count()), (1, 1))
        Report.objects.update(resolved_at=timezone.now() - timedelta(days=367))
        cleanup.run()
        self.assertEqual((Report.objects.count(), Appeal.objects.count()), (0, 0))
