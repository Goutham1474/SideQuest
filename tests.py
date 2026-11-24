#!/usr/bin/env python3
"""Tests for FitLog. Run with: python3 -m unittest -v"""

import datetime as dt
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import app


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB_PATH = os.path.join(self.tmp.name, "test.db")
        app.init_db()
        self.httpd = app.make_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        self.base = f"http://{host}:{port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def call(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read()
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, (json.loads(raw) if raw else None)

    def state(self, days=14):
        status, payload = self.call("GET", f"/api/state?days={days}")
        self.assertEqual(status, 200)
        return payload


class EntryTests(ServerTestCase):
    def test_log_pushups_updates_today(self):
        status, entry = self.call("POST", "/api/entries", {"kind": "pushups", "amount": 25})
        self.assertEqual(status, 201)
        self.assertEqual(entry["amount"], 25)
        self.assertEqual(entry["kind"], "pushups")
        self.assertEqual(entry["day"], dt.date.today().isoformat())

        state = self.state()
        self.assertEqual(state["totals"]["pushups"]["today"], 25)
        self.assertEqual(state["totals"]["steps"]["today"], 0)

    def test_multiple_entries_accumulate(self):
        for amount in (20, 30, 10):
            status, _ = self.call("POST", "/api/entries", {"kind": "pushups", "amount": amount})
            self.assertEqual(status, 201)

        state = self.state()
        self.assertEqual(state["totals"]["pushups"]["today"], 60)
        self.assertEqual(state["lifetime"]["pushups"], 60)
        self.assertEqual(len(state["entries"]), 3)

    def test_steps_and_pushups_are_separate(self):
        self.call("POST", "/api/entries", {"kind": "steps", "amount": 5000})
        self.call("POST", "/api/entries", {"kind": "pushups", "amount": 40})

        state = self.state()
        self.assertEqual(state["totals"]["steps"]["today"], 5000)
        self.assertEqual(state["totals"]["pushups"]["today"], 40)

    def test_backdated_entry_appears_in_series(self):
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        status, entry = self.call(
            "POST", "/api/entries", {"kind": "steps", "amount": 9000, "day": yesterday}
        )
        self.assertEqual(status, 201)
        self.assertEqual(entry["day"], yesterday)

        state = self.state(days=7)
        by_day = {item["day"]: item["steps"] for item in state["days"]}
        self.assertEqual(by_day[yesterday], 9000)
        self.assertEqual(state["totals"]["steps"]["today"], 0)

    def test_delete_entry(self):
        _, entry = self.call("POST", "/api/entries", {"kind": "pushups", "amount": 15})

        status, body = self.call("DELETE", f"/api/entries/{entry['id']}")
        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertEqual(self.state()["totals"]["pushups"]["today"], 0)

        status, body = self.call("DELETE", f"/api/entries/{entry['id']}")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "entry not found")

    def test_delete_unknown_path(self):
        status, _ = self.call("DELETE", "/api/entries/not-a-number")
        self.assertEqual(status, 404)


class ValidationTests(ServerTestCase):
    def test_rejects_bad_kind(self):
        status, body = self.call("POST", "/api/entries", {"kind": "squats", "amount": 10})
        self.assertEqual(status, 400)
        self.assertIn("kind", body["error"])

    def test_rejects_bad_amounts(self):
        for amount in (0, -5, "12", None, True, 2.5, 10**9):
            status, _ = self.call("POST", "/api/entries", {"kind": "pushups", "amount": amount})
            self.assertEqual(status, 400, f"amount={amount!r} should be rejected")

    def test_rejects_future_day(self):
        tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
        status, body = self.call(
            "POST", "/api/entries", {"kind": "steps", "amount": 100, "day": tomorrow}
        )
        self.assertEqual(status, 400)
        self.assertIn("future", body["error"])

    def test_rejects_malformed_day(self):
        status, _ = self.call(
            "POST", "/api/entries", {"kind": "steps", "amount": 100, "day": "24-11-2026"}
        )
        self.assertEqual(status, 400)

    def test_rejects_invalid_json(self):
        request = urllib.request.Request(
            self.base + "/api/entries",
            data=b"{not json",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_endpoint(self):
        status, _ = self.call("GET", "/api/nope")
        self.assertEqual(status, 404)


class SettingsTests(ServerTestCase):
    def test_default_goals(self):
        goals = self.state()["goals"]
        self.assertEqual(goals["pushups"], 100)
        self.assertEqual(goals["steps"], 10000)

    def test_update_goals(self):
        status, body = self.call("PUT", "/api/settings", {"pushups": 150, "steps": 12000})
        self.assertEqual(status, 200)
        self.assertEqual(body["goals"], {"pushups": 150, "steps": 12000})
        self.assertEqual(self.state()["goals"]["pushups"], 150)

    def test_partial_update_keeps_other_goal(self):
        self.call("PUT", "/api/settings", {"steps": 11000})
        goals = self.state()["goals"]
        self.assertEqual(goals["steps"], 11000)
        self.assertEqual(goals["pushups"], 100)

    def test_rejects_bad_goals(self):
        for payload in ({"pushups": 0}, {"steps": -1}, {"pushups": "lots"}, {"steps": 1.5}):
            status, _ = self.call("PUT", "/api/settings", payload)
            self.assertEqual(status, 400, f"{payload} should be rejected")

    def test_rejects_empty_update(self):
        status, _ = self.call("PUT", "/api/settings", {})
        self.assertEqual(status, 400)


class StreakTests(unittest.TestCase):
    def test_counts_consecutive_days_at_goal(self):
        today = dt.date(2026, 11, 24)
        totals = {
            "2026-11-24": 120,
            "2026-11-23": 100,
            "2026-11-22": 150,
            "2026-11-21": 40,
        }
        self.assertEqual(app.current_streak(totals, 100, today), 3)

    def test_today_unmet_still_counts_yesterday_back(self):
        today = dt.date(2026, 11, 24)
        totals = {"2026-11-23": 100, "2026-11-22": 100}
        self.assertEqual(app.current_streak(totals, 100, today), 2)

    def test_broken_streak_is_zero(self):
        today = dt.date(2026, 11, 24)
        totals = {"2026-11-10": 500}
        self.assertEqual(app.current_streak(totals, 100, today), 0)

    def test_empty_history(self):
        self.assertEqual(app.current_streak({}, 100, dt.date(2026, 11, 24)), 0)


class GameTests(ServerTestCase):
    def test_game_payload_shape(self):
        game = self.state()["game"]
        for key in ("xp", "level", "title", "progress", "toNext", "badges",
                    "quests", "badgesEarned", "badgesTotal", "week"):
            self.assertIn(key, game)
        self.assertEqual(len(game["quests"]), 3)
        self.assertGreaterEqual(game["badgesTotal"], 15)
        self.assertEqual(game["xp"], 0)
        self.assertEqual(game["level"], 1)
        self.assertEqual(game["title"], "Rookie")
        self.assertEqual(game["badgesEarned"], 0)

    def test_xp_and_level_progression(self):
        self.call("POST", "/api/entries", {"kind": "pushups", "amount": 1000})
        game = self.state()["game"]
        # 1000 pushups + 0 steps + 20 consistency bonus for one active day.
        self.assertEqual(game["xp"], 1020)
        self.assertEqual(game["level"], 3)
        self.assertEqual(game["title"], "Regular")
        self.assertEqual(game["toNext"], 780)

    def test_daily_quests_track_goals(self):
        self.call("PUT", "/api/settings", {"pushups": 10, "steps": 1000})
        self.call("POST", "/api/entries", {"kind": "pushups", "amount": 15})
        self.call("POST", "/api/entries", {"kind": "steps", "amount": 1200})

        game = self.state()["game"]
        by_id = {quest["id"]: quest for quest in game["quests"]}
        self.assertTrue(by_id["pushup-goal"]["done"])
        self.assertTrue(by_id["step-goal"]["done"])
        self.assertGreaterEqual(game["questsDone"], 2)
        self.assertEqual(len(game["quests"]), 3)

    def test_badges_unlock_from_activity(self):
        self.call("POST", "/api/entries", {"kind": "pushups", "amount": 100})
        badges = {badge["id"]: badge for badge in self.state()["game"]["badges"]}
        self.assertTrue(badges["first-step"]["earned"])
        self.assertTrue(badges["goal-getter"]["earned"])
        self.assertTrue(badges["century"]["earned"])
        self.assertFalse(badges["double-century"]["earned"])
        self.assertEqual(badges["double-century"]["progress"],
                         {"current": 100, "target": 200})
        self.assertFalse(badges["thousand-reps"]["earned"])
        self.assertEqual(badges["thousand-reps"]["progress"]["target"], 1000)

    def test_week_progress_counts_active_days(self):
        self.call("POST", "/api/entries", {"kind": "steps", "amount": 500})
        week = self.state()["game"]["week"]
        self.assertEqual(week["target"], 5)
        self.assertGreaterEqual(week["activeDays"], 1)
        self.assertLessEqual(week["activeDays"], 7)

    def test_streak_and_perfect_day_badges(self):
        self.call("PUT", "/api/settings", {"pushups": 10, "steps": 1000})
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        today = dt.date.today().isoformat()
        for day in (yesterday, today):
            self.call("POST", "/api/entries",
                      {"kind": "pushups", "amount": 20, "day": day})
            self.call("POST", "/api/entries",
                      {"kind": "steps", "amount": 2000, "day": day})

        game = self.state()["game"]
        badges = {badge["id"]: badge for badge in game["badges"]}
        self.assertTrue(badges["perfect-day"]["earned"])
        self.assertEqual(game["week"]["goalDays"], 2)
        self.assertEqual(game["badgesEarned"],
                         sum(1 for badge in game["badges"] if badge["earned"]))


class LevelCurveTests(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(app.level_threshold(1), 0)
        self.assertEqual(app.level_threshold(2), 400)
        self.assertEqual(app.level_threshold(3), 1000)
        self.assertEqual(app.level_threshold(4), 1800)

    def test_level_lookup(self):
        self.assertEqual(app.level_info(0)["level"], 1)
        self.assertEqual(app.level_info(399)["level"], 1)
        self.assertEqual(app.level_info(400)["level"], 2)
        self.assertEqual(app.level_info(999)["level"], 2)
        self.assertEqual(app.level_info(1000)["level"], 3)
        self.assertEqual(app.level_info(1000)["toNext"], 800)

    def test_titles(self):
        self.assertEqual(app.level_info(0)["title"], "Rookie")
        self.assertEqual(app.level_info(1000)["title"], "Regular")
        self.assertEqual(app.level_info(2800)["title"], "Mover")
        self.assertEqual(app.level_info(5400)["title"], "Athlete")

    def test_progress_is_clamped(self):
        for xp in (0, 399, 400, 100000):
            info = app.level_info(xp)
            self.assertGreaterEqual(info["progress"], 0)
            self.assertLessEqual(info["progress"], 1)


class StaticAndExportTests(ServerTestCase):
    def test_index_is_served(self):
        with urllib.request.urlopen(self.base + "/", timeout=5) as response:
            self.assertEqual(response.status, 200)
            html = response.read().decode("utf-8")
        self.assertIn("FitLog", html)
        self.assertIn("/app.js", html)

    def test_css_and_js_are_served_with_correct_types(self):
        for path, expected_type in (("/style.css", "text/css"), ("/app.js", "text/javascript")):
            with urllib.request.urlopen(self.base + path, timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(expected_type, response.headers["Content-Type"])

    def test_missing_static_file_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.base + "/nope.html", timeout=5)
        self.assertEqual(ctx.exception.code, 404)

    def test_csv_export(self):
        self.call("POST", "/api/entries", {"kind": "pushups", "amount": 30})
        self.call("POST", "/api/entries", {"kind": "steps", "amount": 4200, "day": "2026-01-02"})

        with urllib.request.urlopen(self.base + "/api/export.csv", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/csv", response.headers["Content-Type"])
            self.assertIn("attachment", response.headers["Content-Disposition"])
            body = response.read().decode("utf-8")

        lines = body.strip().splitlines()
        self.assertEqual(lines[0], "day,kind,amount,created_at")
        self.assertIn(",pushups,30,", body)
        self.assertIn("2026-01-02,steps,4200,", body)

    def test_state_range_is_clamped(self):
        state = self.state(days=5000)
        self.assertEqual(len(state["days"]), 365)


if __name__ == "__main__":
    unittest.main(verbosity=2)
