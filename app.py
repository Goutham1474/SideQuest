#!/usr/bin/env python3
"""FitLog - a tiny, dependency-free fitness tracker for pushups and steps.

Run it with:

    python3 app.py

then open http://localhost:8756 in a browser.

Everything lives in a single SQLite file (fitlog.db) next to this script.
Only the Python standard library is used, so there is nothing to install.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sqlite3
import sys
import traceback
import webbrowser
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.environ.get("FITLOG_DB", os.path.join(BASE_DIR, "fitlog.db"))

KIND_ORDER = ("pushups", "steps")
KINDS = frozenset(KIND_ORDER)
DEFAULT_GOALS = {"pushups": 100, "steps": 10000}
MAX_AMOUNT = 200_000
MAX_GOAL = 100_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    day        TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('pushups', 'steps')),
    amount     INTEGER NOT NULL CHECK (amount > 0),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entries_day_kind ON entries (day, kind);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------

@contextmanager
def db():
    """Open a short-lived connection and commit on success."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
        for kind in KIND_ORDER:
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (f"goal_{kind}", str(DEFAULT_GOALS[kind])),
            )


def load_goals(conn: sqlite3.Connection) -> dict:
    goals = dict(DEFAULT_GOALS)
    for row in conn.execute("SELECT key, value FROM settings"):
        key = row["key"]
        if key.startswith("goal_"):
            kind = key[len("goal_"):]
            if kind in KINDS:
                try:
                    goals[kind] = int(row["value"])
                except (TypeError, ValueError):
                    pass
    return goals


def set_goal(conn: sqlite3.Connection, kind: str, value: int) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (f"goal_{kind}", str(value)),
    )


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def clean_kind(value) -> str:
    if value not in KINDS:
        raise ValueError("kind must be 'pushups' or 'steps'")
    return value


def clean_amount(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("amount must be a number")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("amount must be a whole number")
        value = int(value)
    if not 1 <= value <= MAX_AMOUNT:
        raise ValueError(f"amount must be between 1 and {MAX_AMOUNT:,}")
    return value


def clean_day(value) -> str:
    if value is None or value == "":
        return dt.date.today().isoformat()
    if not isinstance(value, str):
        raise ValueError("day must be a YYYY-MM-DD string")
    try:
        day = dt.date.fromisoformat(value)
    except ValueError:
        raise ValueError("day must be a valid YYYY-MM-DD date") from None
    today = dt.date.today()
    if day > today:
        raise ValueError("cannot log a future date")
    if day < dt.date(2000, 1, 1):
        raise ValueError("date is too far in the past")
    return day.isoformat()


def clean_goal(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("goal must be a whole number")
    if not 1 <= value <= MAX_GOAL:
        raise ValueError(f"goal must be between 1 and {MAX_GOAL:,}")
    return value


# --------------------------------------------------------------------------
# State assembly
# --------------------------------------------------------------------------

def current_streak(totals_by_day: dict, goal: int, today: dt.date) -> int:
    """Consecutive days (ending today or yesterday) where the goal was met."""
    cursor = today
    if totals_by_day.get(cursor.isoformat(), 0) < goal:
        cursor -= dt.timedelta(days=1)
    streak = 0
    while totals_by_day.get(cursor.isoformat(), 0) >= goal:
        streak += 1
        cursor -= dt.timedelta(days=1)
    return streak


def longest_streak(totals_by_day: dict, goal: int) -> int:
    """Longest run of consecutive days at or above the goal, all time."""
    best = 0
    run = 0
    previous = None
    for day_str in sorted(totals_by_day):
        if totals_by_day[day_str] < goal:
            run = 0
            previous = None
            continue
        day = dt.date.fromisoformat(day_str)
        run = run + 1 if previous and (day - previous).days == 1 else 1
        best = max(best, run)
        previous = day
    return best


def active_streak(active_days, today: dt.date) -> int:
    """Consecutive days with any activity, ending today or yesterday."""
    cursor = today
    if cursor.isoformat() not in active_days:
        cursor -= dt.timedelta(days=1)
    streak = 0
    while cursor.isoformat() in active_days:
        streak += 1
        cursor -= dt.timedelta(days=1)
    return streak


def longest_perfect_run(day_totals: dict, goals: dict) -> int:
    """Longest run of days where both daily goals were met."""
    best = 0
    run = 0
    previous = None
    for day_str in sorted(day_totals):
        totals = day_totals[day_str]
        if (totals["pushups"] < goals["pushups"]
                or totals["steps"] < goals["steps"]):
            run = 0
            previous = None
            continue
        day = dt.date.fromisoformat(day_str)
        run = run + 1 if previous and (day - previous).days == 1 else 1
        best = max(best, run)
        previous = day
    return best


LEVEL_TITLES = (
    (1, "Rookie"),
    (3, "Regular"),
    (5, "Mover"),
    (7, "Athlete"),
    (10, "Beast"),
    (15, "Legend"),
)


def level_threshold(level: int) -> int:
    """Total XP needed to reach a level. Grows quadratically."""
    return 100 * (level - 1) * (level + 2)


def level_title(level: int) -> str:
    title = LEVEL_TITLES[0][1]
    for minimum, name in LEVEL_TITLES:
        if level >= minimum:
            title = name
    return title


def level_info(xp: int) -> dict:
    level = 1
    while level < 100 and xp >= level_threshold(level + 1):
        level += 1
    start = level_threshold(level)
    end = level_threshold(level + 1) if level < 100 else start
    span = max(1, end - start)
    return {
        "level": level,
        "title": level_title(level),
        "levelStart": start,
        "levelEnd": end,
        "progress": round(min(1.0, max(0.0, (xp - start) / span)), 4),
        "toNext": max(0, end - xp),
    }


def build_quests(today_totals: dict, yesterday_totals: dict,
                 today_entries: int, goals: dict) -> list:
    """Three daily quests. The bonus quest rotates deterministically by date."""
    pushups = today_totals["pushups"]
    steps = today_totals["steps"]
    pushup_goal = goals["pushups"]
    step_goal = goals["steps"]

    quests = [
        {
            "id": "pushup-goal",
            "kind": "pushups",
            "label": "Complete your pushup goal",
            "detail": f"{pushups:,} / {pushup_goal:,} pushups",
            "progress": {"current": min(pushups, pushup_goal), "target": pushup_goal},
            "done": pushups >= pushup_goal,
        },
        {
            "id": "step-goal",
            "kind": "steps",
            "label": "Complete your step goal",
            "detail": f"{steps:,} / {step_goal:,} steps",
            "progress": {"current": min(steps, step_goal), "target": step_goal},
            "done": steps >= step_goal,
        },
    ]

    rotation = dt.date.today().toordinal() % 4
    if rotation == 0:
        bonus = {
            "id": "outdo-yesterday",
            "kind": "bonus",
            "label": "Outdo yesterday",
            "detail": f"{pushups:,} pushups · {steps:,} steps so far",
            "progress": None,
            "done": (pushups > yesterday_totals["pushups"]
                     and steps > yesterday_totals["steps"]),
        }
    elif rotation == 1:
        target = 3
        bonus = {
            "id": "three-sessions",
            "kind": "bonus",
            "label": "Log three sessions today",
            "detail": f"{min(today_entries, target)} / {target} entries",
            "progress": {"current": min(today_entries, target), "target": target},
            "done": today_entries >= target,
        }
    elif rotation == 2:
        target = pushup_goal + 50
        bonus = {
            "id": "pushup-bonus",
            "kind": "bonus",
            "label": "Push 50 past your goal",
            "detail": f"{pushups:,} / {target:,} pushups",
            "progress": {"current": min(pushups, target), "target": target},
            "done": pushups >= target,
        }
    else:
        target = step_goal + 2000
        bonus = {
            "id": "step-bonus",
            "kind": "bonus",
            "label": "Walk 2,000 extra steps",
            "detail": f"{steps:,} / {target:,} steps",
            "progress": {"current": min(steps, target), "target": target},
            "done": steps >= target,
        }

    quests.append(bonus)
    return quests


def build_badges(stats: dict) -> list:
    """Achievements derived entirely from activity history."""
    def make(key, name, description, tier, icon, earned, current, target):
        item = {
            "id": key,
            "name": name,
            "description": description,
            "tier": tier,
            "icon": icon,
            "earned": bool(earned),
        }
        if not earned:
            item["progress"] = {
                "current": min(current, target),
                "target": target,
            }
        return item

    return [
        make("first-step", "First Step", "Log your first activity",
             "bronze", "spark", stats["entries"] >= 1, stats["entries"], 1),
        make("goal-getter", "Goal Getter", "Meet any daily goal",
             "bronze", "target", stats["goalDaysAny"] >= 1, stats["goalDaysAny"], 1),
        make("on-a-roll", "On a Roll", "Hit a goal three days in a row",
             "bronze", "flame", stats["longestGoal"] >= 3, stats["longestGoal"], 3),
        make("week-warrior", "Week Warrior", "Hit a goal seven days in a row",
             "silver", "calendar", stats["longestGoal"] >= 7, stats["longestGoal"], 7),
        make("unstoppable", "Unstoppable", "Hit a goal thirty days in a row",
             "gold", "mountain", stats["longestGoal"] >= 30, stats["longestGoal"], 30),
        make("century", "Century", "100 pushups in one day",
             "silver", "trophy", stats["bestPushups"] >= 100, stats["bestPushups"], 100),
        make("double-century", "Double Century", "200 pushups in one day",
             "gold", "bolt", stats["bestPushups"] >= 200, stats["bestPushups"], 200),
        make("ten-k", "10K Club", "10,000 steps in one day",
             "silver", "footsteps", stats["bestSteps"] >= 10_000, stats["bestSteps"], 10_000),
        make("perfect-day", "Perfect Day", "Meet both goals in one day",
             "silver", "check", stats["perfectDays"] >= 1, stats["perfectDays"], 1),
        make("perfect-week", "Perfect Week", "Meet both goals seven days straight",
             "gold", "crown", stats["perfectRun"] >= 7, stats["perfectRun"], 7),
        make("thousand-reps", "Thousand Reps", "1,000 lifetime pushups",
             "silver", "dumbbell", stats["pushups"] >= 1_000, stats["pushups"], 1_000),
        make("globetrotter", "Globetrotter", "100,000 lifetime steps",
             "bronze", "globe", stats["steps"] >= 100_000, stats["steps"], 100_000),
        make("million-steps", "Million Steps", "1,000,000 lifetime steps",
             "gold", "compass", stats["steps"] >= 1_000_000, stats["steps"], 1_000_000),
        make("early-bird", "Early Bird", "Log a set before 8 AM",
             "bronze", "sun", stats["early"] >= 1, stats["early"], 1),
        make("night-owl", "Night Owl", "Log a set after 10 PM",
             "bronze", "moon", stats["late"] >= 1, stats["late"], 1),
        make("level-5", "Rising Star", "Reach level 5",
             "silver", "star", stats["level"] >= 5, stats["level"], 5),
        make("level-10", "Peak Form", "Reach level 10",
             "gold", "medal", stats["level"] >= 10, stats["level"], 10),
    ]


def build_state(days: int = 14, entry_limit: int = 15) -> dict:
    days = max(1, min(int(days), 365))
    today = dt.date.today()
    start = today - dt.timedelta(days=days - 1)

    with db() as conn:
        goals = load_goals(conn)
        rows = conn.execute(
            "SELECT day, kind, SUM(amount) AS total FROM entries"
            " WHERE day >= ? GROUP BY day, kind",
            (start.isoformat(),),
        ).fetchall()
        entries = conn.execute(
            "SELECT id, day, kind, amount, created_at FROM entries"
            " WHERE day >= ? ORDER BY day DESC, created_at DESC, id DESC LIMIT ?",
            (start.isoformat(), entry_limit),
        ).fetchall()
        lifetime_rows = conn.execute(
            "SELECT kind, SUM(amount) AS total FROM entries GROUP BY kind"
        ).fetchall()
        all_day_rows = conn.execute(
            "SELECT day, kind, SUM(amount) AS total FROM entries GROUP BY day, kind"
        ).fetchall()
        entry_stats = conn.execute(
            "SELECT COUNT(*) AS total,"
            " COALESCE(SUM(CASE WHEN substr(created_at, 12, 5) < '08:00'"
            "                   THEN 1 ELSE 0 END), 0) AS early,"
            " COALESCE(SUM(CASE WHEN substr(created_at, 12, 5) >= '22:00'"
            "                   THEN 1 ELSE 0 END), 0) AS late"
            " FROM entries"
        ).fetchone()
        today_entry_count = conn.execute(
            "SELECT COUNT(*) AS count FROM entries WHERE day = ?",
            (today.isoformat(),),
        ).fetchone()["count"]

    sums = {(r["day"], r["kind"]): r["total"] for r in rows}
    series = []
    for offset in range(days):
        day = (start + dt.timedelta(days=offset)).isoformat()
        series.append({
            "day": day,
            "pushups": sums.get((day, "pushups"), 0),
            "steps": sums.get((day, "steps"), 0),
        })

    totals = {
        kind: {"today": series[-1][kind], "range": 0, "best": 0, "daysMet": 0}
        for kind in KIND_ORDER
    }
    for item in series:
        for kind in KIND_ORDER:
            value = item[kind]
            bucket = totals[kind]
            bucket["range"] += value
            bucket["best"] = max(bucket["best"], value)
            if value >= goals[kind]:
                bucket["daysMet"] += 1
    for kind in KIND_ORDER:
        totals[kind]["avg"] = round(totals[kind]["range"] / days, 1)

    by_day = {kind: {} for kind in KIND_ORDER}
    day_totals = {}
    for row in all_day_rows:
        if row["kind"] in by_day:
            by_day[row["kind"]][row["day"]] = row["total"]
        bucket = day_totals.setdefault(row["day"], {"pushups": 0, "steps": 0})
        if row["kind"] in bucket:
            bucket[row["kind"]] = row["total"]

    lifetime = {kind: 0 for kind in KIND_ORDER}
    for row in lifetime_rows:
        if row["kind"] in lifetime:
            lifetime[row["kind"]] = row["total"]

    # ---------- game layer (all derived, nothing extra persisted) ----------
    active_days = set(day_totals)
    perfect_days = sum(
        1 for day in day_totals.values()
        if day["pushups"] >= goals["pushups"] and day["steps"] >= goals["steps"]
    )
    goal_days_any = sum(
        1 for day in day_totals.values()
        if day["pushups"] >= goals["pushups"] or day["steps"] >= goals["steps"]
    )
    best_pushups = max((day["pushups"] for day in day_totals.values()), default=0)
    best_steps = max((day["steps"] for day in day_totals.values()), default=0)
    longest_goal = max(
        longest_streak(by_day["pushups"], goals["pushups"]),
        longest_streak(by_day["steps"], goals["steps"]),
    )
    longest_perfect = longest_perfect_run(day_totals, goals)

    xp = lifetime["pushups"] + lifetime["steps"] // 100 + 20 * len(active_days)
    level = level_info(xp)

    quests = build_quests(
        day_totals.get(today.isoformat(), {"pushups": 0, "steps": 0}),
        day_totals.get((today - dt.timedelta(days=1)).isoformat(),
                       {"pushups": 0, "steps": 0}),
        today_entry_count,
        goals,
    )

    week_start = today - dt.timedelta(days=today.weekday())
    week_days = [
        (week_start + dt.timedelta(days=offset)).isoformat()
        for offset in range(7)
    ]
    week_active = sum(1 for day in week_days if day in day_totals)
    week_goal_days = sum(
        1 for day in week_days
        if day in day_totals and (
            day_totals[day]["pushups"] >= goals["pushups"]
            or day_totals[day]["steps"] >= goals["steps"]
        )
    )

    badges = build_badges({
        "entries": entry_stats["total"],
        "early": entry_stats["early"],
        "late": entry_stats["late"],
        "pushups": lifetime["pushups"],
        "steps": lifetime["steps"],
        "bestPushups": best_pushups,
        "bestSteps": best_steps,
        "longestGoal": longest_goal,
        "perfectDays": perfect_days,
        "perfectRun": longest_perfect,
        "goalDaysAny": goal_days_any,
        "level": level["level"],
    })

    return {
        "today": today.isoformat(),
        "days": series,
        "goals": goals,
        "totals": totals,
        "streaks": {
            kind: current_streak(by_day[kind], goals[kind], today)
            for kind in KIND_ORDER
        },
        "lifetime": lifetime,
        "entries": [dict(row) for row in entries],
        "game": {
            "xp": xp,
            "level": level["level"],
            "title": level["title"],
            "levelStart": level["levelStart"],
            "levelEnd": level["levelEnd"],
            "progress": level["progress"],
            "toNext": level["toNext"],
            "streak": active_streak(active_days, today),
            "badges": badges,
            "badgesEarned": sum(1 for badge in badges if badge["earned"]),
            "badgesTotal": len(badges),
            "quests": quests,
            "questsDone": sum(1 for quest in quests if quest["done"]),
            "week": {
                "activeDays": week_active,
                "goalDays": week_goal_days,
                "target": 5,
            },
        },
    }


# --------------------------------------------------------------------------
# HTTP layer
# --------------------------------------------------------------------------

def _int_query(query: dict, name: str, default: int, low: int, high: int) -> int:
    raw = (query.get(name) or [None])[0]
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a whole number") from None
    return max(low, min(value, high))


class Handler(SimpleHTTPRequestHandler):
    server_version = "FitLog/1.0"

    # Quieter logs unless explicitly requested.
    def log_message(self, fmt, *args):
        if os.environ.get("FITLOG_VERBOSE"):
            super().log_message(fmt, *args)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    # ---------- plumbing ----------
    def _dispatch(self, action):
        try:
            action()
        except ValueError as exc:
            self._error(400, str(exc))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # noqa: BLE001 - surface real errors as JSON
            if os.environ.get("FITLOG_VERBOSE"):
                traceback.print_exc()
            self._error(500, f"server error: {exc}")

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._send_json({"error": message}, status)

    def _read_json(self) -> dict:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or 0)
        except (TypeError, ValueError):
            raise ValueError("invalid Content-Length") from None
        if length > 1_000_000:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("request body must be valid JSON") from None
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    # ---------- verbs ----------
    def do_GET(self):
        self._dispatch(self._get)

    def do_POST(self):
        self._dispatch(self._post)

    def do_PUT(self):
        self._dispatch(self._put)

    def do_DELETE(self):
        self._dispatch(self._delete)

    def _get(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/state":
            days = _int_query(parse_qs(parsed.query), "days", 14, 1, 365)
            self._send_json(build_state(days))
            return

        if path == "/api/export.csv":
            self._export_csv()
            return

        if path.startswith("/api/"):
            self._error(404, "unknown endpoint")
            return

        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def _post(self):
        path = urlparse(self.path).path
        if path != "/api/entries":
            self._error(404, "unknown endpoint")
            return

        data = self._read_json()
        kind = clean_kind(data.get("kind"))
        amount = clean_amount(data.get("amount"))
        day = clean_day(data.get("day"))
        created = dt.datetime.now().replace(microsecond=0).isoformat()

        with db() as conn:
            cursor = conn.execute(
                "INSERT INTO entries (day, kind, amount, created_at)"
                " VALUES (?, ?, ?, ?)",
                (day, kind, amount, created),
            )
            entry_id = cursor.lastrowid

        self._send_json(
            {
                "id": entry_id,
                "day": day,
                "kind": kind,
                "amount": amount,
                "created_at": created,
            },
            status=201,
        )

    def _put(self):
        path = urlparse(self.path).path
        if path != "/api/settings":
            self._error(404, "unknown endpoint")
            return

        data = self._read_json()
        updates = {}
        for kind in KIND_ORDER:
            if kind in data:
                updates[kind] = clean_goal(data[kind])
        if not updates:
            raise ValueError("provide at least one goal to update")

        with db() as conn:
            for kind, value in updates.items():
                set_goal(conn, kind, value)
            goals = load_goals(conn)

        self._send_json({"goals": goals})

    def _delete(self):
        path = urlparse(self.path).path
        match = re.fullmatch(r"/api/entries/(\d+)", path)
        if not match:
            self._error(404, "unknown endpoint")
            return

        with db() as conn:
            cursor = conn.execute("DELETE FROM entries WHERE id = ?", (int(match.group(1)),))
            deleted = cursor.rowcount

        if not deleted:
            self._error(404, "entry not found")
            return

        self.send_response(204)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    # ---------- CSV ----------
    def _export_csv(self) -> None:
        with db() as conn:
            rows = conn.execute(
                "SELECT day, kind, amount, created_at FROM entries"
                " ORDER BY day, kind, id"
            ).fetchall()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["day", "kind", "amount", "created_at"])
        for row in rows:
            writer.writerow([row["day"], row["kind"], row["amount"], row["created_at"]])

        body = buffer.getvalue().encode("utf-8")
        filename = f"fitlog-{dt.date.today().isoformat()}.csv"
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


Handler.extensions_map = {
    **SimpleHTTPRequestHandler.extensions_map,
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".svg": "image/svg+xml",
    ".json": "application/json",
}


def make_server(host: str = "127.0.0.1", port: int = 8756) -> ThreadingHTTPServer:
    handler = partial(Handler, directory=STATIC_DIR)
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    return httpd


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="FitLog - pushups and steps tracker")
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address (use 0.0.0.0 to open from your phone)")
    parser.add_argument("--port", type=int, default=8756, help="port to listen on")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)

    init_db()
    httpd = make_server(args.host, args.port)
    port = httpd.server_address[1]
    display_host = "localhost" if args.host in ("127.0.0.1", "0.0.0.0") else args.host
    url = f"http://{display_host}:{port}/"

    print(f"FitLog is running at {url}")
    print(f"Database: {DB_PATH}")
    if args.host == "0.0.0.0":
        print("Phone tip: open http://<your-mac-ip>:{} while on the same Wi-Fi.".format(port))
    print("Press Ctrl+C to stop.")

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping FitLog.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
