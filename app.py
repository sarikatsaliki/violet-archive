"""
Gothic Lavender Productivity App
Flask + SQLite. Tracks habits, rewards, reflections, books & movies.

Database:
  habits, habit_entries, reflections, rewards, media
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB_PATH = Path(__file__).parent / "habittracker.db"

# Sticker options for habit entries
STICKERS = ["🌸", "⭐", "💻", "📚", "🌙", "☕", "🎀", "✨"]


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create database tables and run migrations."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS habit_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            entry_date DATE NOT NULL,
            hours REAL NOT NULL,
            note TEXT,
            sticker TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        );

        CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date DATE NOT NULL UNIQUE,
            reflection_text TEXT,
            win TEXT,
            improvement TEXT,
            mood TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            requirement_type TEXT NOT NULL,
            requirement_value INTEGER NOT NULL,
            unlocked INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            rating INTEGER NOT NULL,
            review TEXT
        );
    """)
    try:
        conn.execute("ALTER TABLE habit_entries ADD COLUMN sticker TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


@app.route("/")
def index():
    """Redirect to dashboard."""
    return redirect(url_for("dashboard"))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    """Dashboard - add/delete habits, log time entries, show totals."""
    today = date.today().isoformat()
    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_habit":
            name = request.form.get("habit_name", "").strip()
            if name:
                try:
                    conn.execute("INSERT INTO habits (name) VALUES (?)", (name,))
                except sqlite3.IntegrityError:
                    pass  # habit name already exists

        elif action == "delete_habit":
            habit_id = request.form.get("habit_id", type=int)
            if habit_id:
                conn.execute("DELETE FROM habit_entries WHERE habit_id = ?", (habit_id,))
                conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))

        elif action == "add_entry":
            habit_id = request.form.get("habit_id", type=int)
            hours = request.form.get("hours", type=float, default=0)
            note = request.form.get("note", "").strip()
            sticker = request.form.get("sticker", "").strip() or None
            if habit_id and hours and hours > 0:
                conn.execute(
                    "INSERT INTO habit_entries (habit_id, entry_date, hours, note, sticker) VALUES (?, ?, ?, ?, ?)",
                    (habit_id, today, hours, note or None, sticker),
                )

        elif action == "add_reward":
            name = request.form.get("reward_name", "").strip()
            req_type = request.form.get("requirement_type", "hours")
            req_value = request.form.get("requirement_value", type=int, default=1)
            if name and req_value and req_value > 0:
                conn.execute(
                    "INSERT INTO rewards (name, requirement_type, requirement_value, unlocked) VALUES (?, ?, ?, 0)",
                    (name, req_type, req_value),
                )

        elif action == "unlock_reward":
            reward_id = request.form.get("reward_id", type=int)
            if reward_id:
                conn.execute("UPDATE rewards SET unlocked = 1 WHERE id = ?", (reward_id,))

        elif action == "delete_reward":
            reward_id = request.form.get("reward_id", type=int)
            if reward_id:
                conn.execute("DELETE FROM rewards WHERE id = ?", (reward_id,))

        conn.commit()

    # Load all habits
    habits = conn.execute("SELECT * FROM habits ORDER BY name").fetchall()

    # For each habit, get today's entries and total
    habit_data = []
    total_hours = 0

    for habit in habits:
        entries = conn.execute(
            "SELECT * FROM habit_entries WHERE habit_id = ? AND entry_date = ? ORDER BY id",
            (habit["id"], today),
        ).fetchall()
        habit_total = sum(e["hours"] for e in entries)
        total_hours += habit_total
        habit_data.append(
            {"habit": habit, "entries": entries, "total": habit_total}
        )

    # Streak: consecutive days (going back) with at least one habit entry
    streak = 0
    check_date = date.today()
    while True:
        row = conn.execute(
            "SELECT 1 FROM habit_entries WHERE entry_date = ? LIMIT 1",
            (check_date.isoformat(),),
        ).fetchone()
        if row:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    today_reflection = conn.execute(
        "SELECT mood FROM reflections WHERE entry_date = ?", (today,)
    ).fetchone()
    today_mood = today_reflection["mood"] if today_reflection else None

    rewards = conn.execute(
        "SELECT * FROM rewards ORDER BY unlocked, id"
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        today=today,
        habit_data=habit_data,
        total_hours=total_hours,
        streak=streak,
        today_mood=today_mood,
        stickers=STICKERS,
        rewards=rewards,
    )


@app.route("/reflection", methods=["GET", "POST"])
def reflection():
    """Reflection page - daily reflection, win, improvement, mood."""
    today = date.today().isoformat()
    conn = get_db()

    if request.method == "POST":
        reflection_text = request.form.get("reflection_text", "").strip()
        win = request.form.get("win", "").strip()
        improvement = request.form.get("improvement", "").strip()
        mood = request.form.get("mood", "neutral")

        conn.execute(
            """REPLACE INTO reflections (entry_date, reflection_text, win, improvement, mood)
               VALUES (?, ?, ?, ?, ?)""",
            (today, reflection_text, win, improvement, mood),
        )
        conn.commit()

    entry_date = request.args.get("date", today)
    reflection_row = conn.execute(
        "SELECT * FROM reflections WHERE entry_date = ?", (entry_date,)
    ).fetchone()
    conn.close()

    return render_template(
        "reflection.html",
        today=today,
        entry_date=entry_date,
        reflection=dict(reflection_row) if reflection_row else None,
    )


@app.route("/books-movies", methods=["GET", "POST"])
def books_movies():
    """Books & Movies page - add and view entries with rating and review."""
    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_media":
            title = request.form.get("title", "").strip()
            media_type = request.form.get("type", "book")
            rating = request.form.get("rating", type=int, default=3)
            review = request.form.get("review", "").strip() or None
            if title and 1 <= rating <= 5:
                conn.execute(
                    "INSERT INTO media (title, type, rating, review) VALUES (?, ?, ?, ?)",
                    (title, media_type, rating, review),
                )
        elif action == "delete_media":
            media_id = request.form.get("media_id", type=int)
            if media_id:
                conn.execute("DELETE FROM media WHERE id = ?", (media_id,))
        conn.commit()

    entries = conn.execute(
        "SELECT * FROM media ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("books_movies.html", entries=entries)


@app.template_filter("float_format")
def float_format(value):
    """Format float to one decimal place."""
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "0.0"


@app.template_filter("stars")
def stars(rating):
    """Return 1-5 star display string."""
    try:
        r = int(rating)
        r = max(0, min(5, r))
    except (TypeError, ValueError):
        r = 0
    return "★" * r + "☆" * (5 - r)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
