import os
import sqlite3
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, flash, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB_PATH = Path(__file__).parent / "habittracker.db"

STICKERS = ["🌸", "⭐", "💻", "📚", "🌙", "☕", "🎀", "✨"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.template_filter("float_format")
def float_format(value):
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "0.0"
@app.template_filter("stars")
def stars_filter(value):
    try:
        return "★" * int(value) + "☆" * (5 - int(value))
    except (ValueError, TypeError):
        return ""


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id, name),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS habit_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            habit_id INTEGER NOT NULL,
            entry_date DATE NOT NULL,
            hours REAL NOT NULL,
            note TEXT,
            sticker TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            entry_date DATE NOT NULL,
            reflection_text TEXT,
            win TEXT,
            improvement TEXT,
            mood TEXT NOT NULL,
            UNIQUE(user_id, entry_date)
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
    # Ensure multi-user columns exist for databases created before user support
    for table in ("habits", "habit_entries"):
        columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not any(col["name"] == "user_id" for col in columns):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")

    conn.commit()
    conn.close()


# ---------------- AUTH ---------------- #

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password required.")
            return render_template("signup.html")

        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )
            conn.commit()
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            flash("Username already exists.")
            return render_template("signup.html")

        conn.close()

        session["user_id"] = user_id
        session["username"] = username
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if not user:
            flash("No account found with that username. You can sign up to create one.")
            return render_template("login.html")

        if not check_password_hash(user["password_hash"], password):
            flash("Incorrect password.")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    today = date.today().isoformat()
    user_id = session["user_id"]
    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_habit":
            name = request.form.get("habit_name", "").strip()
            if name:
                try:
                    conn.execute(
                        "INSERT INTO habits (user_id, name) VALUES (?, ?)",
                        (user_id, name),
                    )
                except sqlite3.IntegrityError:
                    pass

        elif action == "delete_habit":
            habit_id = request.form.get("habit_id", type=int)
            if habit_id:
                conn.execute(
                    "DELETE FROM habit_entries WHERE habit_id = ? AND user_id = ?",
                    (habit_id, user_id),
                )
                conn.execute(
                    "DELETE FROM habits WHERE id = ? AND user_id = ?",
                    (habit_id, user_id),
                )

        elif action == "add_entry":
            habit_id = request.form.get("habit_id", type=int)
            hours = request.form.get("hours", type=float)
            note = request.form.get("note", "")
            sticker = request.form.get("sticker")
            if habit_id and hours:
                conn.execute(
                    "INSERT INTO habit_entries (user_id, habit_id, entry_date, hours, note, sticker) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, habit_id, today, hours, note, sticker),
                )

        elif action == "add_reward":
            name = request.form.get("reward_name")
            req_type = request.form.get("requirement_type")
            req_value = request.form.get("requirement_value", type=int)
            conn.execute(
                "INSERT INTO rewards (name, requirement_type, requirement_value) VALUES (?, ?, ?)",
                (name, req_type, req_value),
            )

        elif action == "unlock_reward":
            reward_id = request.form.get("reward_id", type=int)
            conn.execute("UPDATE rewards SET unlocked = 1 WHERE id = ?", (reward_id,))

        elif action == "delete_reward":
            reward_id = request.form.get("reward_id", type=int)
            conn.execute("DELETE FROM rewards WHERE id = ?", (reward_id,))

        conn.commit()

    habits = conn.execute(
        "SELECT * FROM habits WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()

    habit_data = []
    total_hours = 0

    for habit in habits:
        entries = conn.execute(
            "SELECT * FROM habit_entries WHERE habit_id = ? AND user_id = ? AND entry_date = ?",
            (habit["id"], user_id, today),
        ).fetchall()
        habit_total = sum(e["hours"] for e in entries)
        total_hours += habit_total
        habit_data.append({"habit": habit, "entries": entries, "total": habit_total})

    streak = 0
    check_date = date.today()
    while True:
        row = conn.execute(
            "SELECT 1 FROM habit_entries WHERE user_id = ? AND entry_date = ? LIMIT 1",
            (user_id, check_date.isoformat()),
        ).fetchone()
        if row:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    today_reflection = conn.execute(
        "SELECT mood FROM reflections WHERE user_id = ? AND entry_date = ?",
        (session["user_id"], today),
    ).fetchone()

    today_mood = today_reflection["mood"] if today_reflection else None

    rewards = conn.execute("SELECT * FROM rewards ORDER BY unlocked, id").fetchall()

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
# ---------------- REFLECTION ---------------- #

@app.route("/reflection", methods=["GET", "POST"])
@login_required
def reflection():
    today = date.today().isoformat()
    conn = get_db()
    
    if request.method == "POST":
        reflection_text = request.form.get("reflection_text")
        win = request.form.get("win")
        improvement = request.form.get("improvement")
        mood = request.form.get("mood")
        
        conn.execute("""
            INSERT INTO reflections (user_id, entry_date, reflection_text, win, improvement, mood)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, entry_date) DO UPDATE SET
                reflection_text=excluded.reflection_text,
                win=excluded.win,
                improvement=excluded.improvement,
                mood=excluded.mood
        """, (session["user_id"], today, reflection_text, win, improvement, mood))
        conn.commit()
        flash("Reflection saved!")
        return redirect(url_for("dashboard"))

    reflection = conn.execute(
        "SELECT * FROM reflections WHERE user_id = ? AND entry_date = ?",
        (session["user_id"], today)
    ).fetchone()
    conn.close()
    
    return render_template("reflection.html", reflection=reflection, entry_date=today)
# ---------------- BOOKS & MOVIES ---------------- #

@app.route("/media", methods=["GET", "POST"])
@login_required
def books_movies():
    conn = get_db()
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_media":
            title = request.form.get("title")
            media_type = request.form.get("type")
            rating = request.form.get("rating")
            review = request.form.get("review")
            conn.execute(
                "INSERT INTO media (title, type, rating, review) VALUES (?, ?, ?, ?)",
                (title, media_type, rating, review)
            )
            
        elif action == "delete_media":
            media_id = request.form.get("media_id")
            conn.execute("DELETE FROM media WHERE id = ?", (media_id,))
            
        conn.commit()
        return redirect(url_for("books_movies"))

    # Fetching the data to show on the page
    entries = conn.execute("SELECT * FROM media ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("books_movies.html", entries=entries)
if __name__ == "__main__":
    init_db()
    app.run(debug=True)