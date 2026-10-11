from django.db import connection
from django.test import override_settings

from contacts import services as contacts

from .base import (
    DORSTEN, FAST_100, HOHENSTEIN, IMMENSTADT, KNAPP_DRAUSSEN, KNAPP_DRIN, UEBER_100, LEIPZIG, MARL, MITTE, MUENSTER, RECKLINGHAUSEN,
    ROSENHEIM, SONTHOFEN, Api, BaseTest, make_user,
)


class RadiusTest(BaseTest):
    def distances(self, *targets):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT b.ags, ST_Distance(a.center, b.center) FROM places a, places b WHERE a.ags = %s AND b.ags = ANY(%s)",
                [MITTE, list(targets)],
            )
            return dict(cur.fetchall())

    def test_default_view_ends_at_20_km_between_municipality_centres(self):
        d = self.distances(KNAPP_DRIN, KNAPP_DRAUSSEN)
        self.assertTrue(19_000 < d[KNAPP_DRIN] < 20_000 < d[KNAPP_DRAUSSEN] < 21_000, d)
        viewer = make_user(residence=MITTE)
        make_user(residence=KNAPP_DRIN)
        make_user(residence=KNAPP_DRAUSSEN)
        api = Api(viewer)
        overview = api.get("/nearby/overview").data
        self.assertEqual((overview["radius_km"], [r["ags"] for r in overview["residences"]]), (20, [KNAPP_DRIN]))
        self.assertEqual(api.get("/nearby/origins", level="state").data["items"][0]["count"], 1)
        self.assertEqual(len(api.get("/nearby/people", home=SONTHOFEN).data["items"]), 1)

    def test_wide_view_ends_at_100_km_and_so_do_profiles_and_requests(self):
        d = self.distances(FAST_100, UEBER_100)
        self.assertTrue(99_000 < d[FAST_100] < 100_000 < d[UEBER_100] < 101_000, d)
        viewer = make_user(residence=MITTE)
        mid = make_user(residence=KNAPP_DRAUSSEN)
        near_edge = make_user(residence=FAST_100)
        beyond = make_user(residence=UEBER_100)
        api = Api(viewer)
        overview = api.get("/nearby/overview", radius_km=100).data
        self.assertEqual(overview["radius_km"], 100)
        self.assertEqual({r["ags"] for r in overview["residences"]}, {KNAPP_DRAUSSEN, FAST_100})
        self.assertEqual(api.get("/nearby/origins", level="state", radius_km=100).data["items"][0]["count"], 2)
        ids = {p["id"] for p in api.get("/nearby/people", home=SONTHOFEN, radius_km=100).data["items"]}
        self.assertEqual(ids, {str(mid.id), str(near_edge.id)})
        # Profile und Anfragen gelten bis 100 km, gleich welche Ansicht gewählt ist.
        self.assertEqual(api.get(f"/users/{near_edge.id}").status_code, 200)
        self.assertEqual(api.post("/requests", {"to_user_id": str(near_edge.id), "body": "Hallo"}).status_code, 201)
        self.assertEqual(api.get(f"/users/{beyond.id}").status_code, 404)
        self.assertEqual(api.post("/requests", {"to_user_id": str(beyond.id), "body": "Hallo"}).status_code, 404)
        self.assertEqual(api.post("/blocks", {"user_id": str(beyond.id)}).status_code, 404)

    def test_only_the_fixed_radius_steps_exist(self):
        api = Api(make_user(residence=MITTE))
        for value in (21, 99, 101, 500, 0, -20):
            for path, extra in (("/nearby/overview", {}), ("/nearby/origins", {"level": "state"}), ("/nearby/people", {"home": SONTHOFEN})):
                response = api.get(path, radius_km=value, **extra)
                self.assertEqual((response.status_code, value), (422, value), path)
        self.assertEqual(api.get("/session").data["site"]["radius_options"], [20, 100])

    def test_client_cannot_move_the_search_centre_or_widen_the_radius(self):
        viewer = make_user(residence=MARL)
        make_user(residence=LEIPZIG)
        data = Api(viewer).get("/nearby/overview", lat=51.34, lon=12.37, radius=1000000, residence=LEIPZIG).data
        self.assertEqual((data["total"], data["radius_km"]), (0, 20))
        self.assertEqual(data["me"]["residence"]["ags"], MARL)


class OriginNetworkTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.viewer = make_user(home=SONTHOFEN, residence=MARL)
        self.same_town = [make_user(home=SONTHOFEN, residence=MARL), make_user(home=SONTHOFEN, residence=RECKLINGHAUSEN)]
        make_user(home=IMMENSTADT, residence=MARL)
        make_user(home=ROSENHEIM, residence=DORSTEN)
        make_user(home=LEIPZIG, residence=MARL)
        make_user(home=HOHENSTEIN, residence=MARL)
        make_user(home=SONTHOFEN, residence=MUENSTER)  # außerhalb des Radius
        self.api = Api(self.viewer)

    def test_overview_groups_by_residence_and_state(self):
        data = self.api.get("/nearby/overview").data
        self.assertEqual(data["total"], 6)
        by_ags = {r["ags"]: r for r in data["residences"]}
        self.assertEqual(set(by_ags), {MARL, RECKLINGHAUSEN, DORSTEN})
        marl = by_ags[MARL]
        self.assertEqual(marl["total"], 4)
        self.assertEqual({s["state_code"]: s["count"] for s in marl["states"]}, {"09": 2, "14": 2})
        self.assertNotIn("users", marl)

    def test_levels_zoom_from_state_to_district_to_place(self):
        states = self.api.get("/nearby/origins", residence="all", level="state").data["items"]
        self.assertEqual([(s["key"], s["name"], s["count"]) for s in states], [("09", "Bayern", 4), ("14", "Sachsen", 2)])
        districts = self.api.get("/nearby/origins", residence="all", level="district", parent="09").data["items"]
        self.assertEqual([(d["key"], d["name"], d["count"]) for d in districts], [("09780", "Oberallgäu", 3), ("09163", "Rosenheim", 1)])
        self.assertEqual(districts[0]["distance_km"] < districts[1]["distance_km"], True)
        places = self.api.get("/nearby/origins", residence="all", level="place", parent="09780").data["items"]
        self.assertEqual([(p["key"], p["count"]) for p in places], [(SONTHOFEN, 2), (IMMENSTADT, 1)])
        self.assertEqual(places[0]["distance_km"], 0)
        # Nur ein Wohnort:
        only_marl = self.api.get("/nearby/origins", residence=MARL, level="place", parent="09780").data["items"]
        self.assertEqual([(p["key"], p["count"]) for p in only_marl], [(IMMENSTADT, 1), (SONTHOFEN, 1)])

    def test_user_data_only_on_place_level(self):
        for level, parent in (("state", None), ("district", "09"), ("place", "09780")):
            params = {"residence": "all", "level": level} | ({"parent": parent} if parent else {})
            for item in self.api.get("/nearby/origins", **params).data["items"]:
                self.assertEqual(set(item), {"key", "name", "count", "distance_km"})
        people = self.api.get("/nearby/people", residence="all", home=SONTHOFEN).data
        self.assertEqual({p["id"] for p in people["items"]}, {str(u.id) for u in self.same_town})
        self.assertEqual(
            set(people["items"][0]), {"id", "nickname", "age_range", "home", "residence", "member_since"}
        )
        self.assertEqual(set(people["items"][0]["residence"]), {"ags", "name"})

    def test_blocking_filters_before_aggregation_in_both_directions(self):
        blocked = self.same_town[0]
        for blocker, target in ((self.viewer, blocked), (blocked, self.viewer)):
            contacts.block(blocker, target.id)
            overview = self.api.get("/nearby/overview").data
            marl = next(r for r in overview["residences"] if r["ags"] == MARL)
            self.assertEqual((overview["total"], marl["total"]), (5, 3))
            self.assertEqual({s["state_code"]: s["count"] for s in marl["states"]}, {"09": 1, "14": 2})
            place = self.api.get("/nearby/origins", residence="all", level="place", parent="09780").data["items"]
            self.assertEqual(dict((p["key"], p["count"]) for p in place)[SONTHOFEN], 1)
            ids = {p["id"] for p in self.api.get("/nearby/people", residence="all", home=SONTHOFEN).data["items"]}
            self.assertNotIn(str(blocked.id), ids)
            self.assertEqual(self.api.get(f"/users/{blocked.id}").status_code, 404)
            self.assertEqual(Api(blocked).get(f"/users/{self.viewer.id}").status_code, 404)
            # Dasselbe aus Sicht der anderen Person.
            other = Api(blocked).get("/nearby/overview").data
            self.assertEqual(other["total"], 5)
            contacts.unblock(blocker, target.id)
        self.assertEqual(self.api.get("/nearby/overview").data["total"], 6)

    def test_empty_surroundings(self):
        lonely = make_user(home=LEIPZIG, residence=MITTE)
        data = Api(lonely).get("/nearby/overview").data
        self.assertEqual((data["total"], data["residences"]), (0, []))

    @override_settings(NEARBY_QUERIES_PER_HOUR=3)
    def test_rate_limit(self):
        for _ in range(3):
            self.assertEqual(self.api.get("/nearby/overview").status_code, 200)
        limited = self.api.get("/nearby/origins", residence="all", level="state")
        self.assertEqual((limited.status_code, limited.data["code"]), (429, "rate_limited"))

    def test_opening_the_surroundings_sets_last_activity_only(self):
        self.assertIsNone(self.viewer.last_activity_at)
        self.api.get("/nearby/overview")
        self.viewer.refresh_from_db()
        self.assertIsNotNone(self.viewer.last_activity_at)


class PlaceSearchTest(BaseTest):
    def test_search_is_public_and_prefix_based(self):
        api = Api()
        self.assertEqual(api.get("/places/search", q="sonth").data["items"][0]["ags"], SONTHOFEN)
        for query in ("Münster", "Muenster", "Munster", "münst"):
            self.assertEqual(api.get("/places/search", q=query).data["items"][0]["name"], "Münster", query)
        self.assertEqual(api.get("/places/search", q="see").data["items"][0]["name"], "Haltern am See")
        self.assertEqual(api.get("/places/search", q="m").data["items"], [])

    def test_nearest_place_for_prefill(self):
        place = Api().post("/places/nearest", {"lat": 51.66, "lon": 7.1}).data["place"]
        self.assertEqual(place["ags"], MARL)
        self.assertEqual(Api().post("/places/nearest", {"lat": 48.85, "lon": 2.35}).status_code, 400)
