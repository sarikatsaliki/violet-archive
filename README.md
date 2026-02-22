# Habit Tracker

A minimal personal habit and reflection web app built with Python Flask and SQLite.

## Setup

1. Create a virtual environment (recommended):
   ```
   python -m venv venv
   venv\Scripts\activate   # Windows
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the app:
   ```
   python app.py
   ```

4. Open http://localhost:5000 in your browser.

## Features

- **Dashboard** – Add and delete habits, log time entries for each habit, see total hours for today. Habits are fully dynamic.
- **Reflection** – Daily reflection text, one win, improvement goal, and mood selection. Entries are saved by date.

## Database Structure

- **habits** – habits you create (add/delete anytime)
- **habit_entries** – time entries for each habit (hours + optional note)
- **reflections** – daily reflection, win, improvement, mood
- **User Authentication** – Secure Sign Up and Login system using password hashing.
- **Books & Movies** – Log media consumption with star ratings and reviews.


## 🌐 Deployment & Data Persistence
This project is configured for deployment on **Render**. 

> **Note:** The live demo uses an SQLite database on Render's free tier. Because the free tier uses an ephemeral file system, data is reset whenever the server restarts or goes to sleep. To maintain a permanent database, run the project locally or connect a persistent PostgreSQL instance.


## Project Structure

```
habittracker/
├── app.py              # Main Flask application (Routes, Auth, and DB init)
├── requirements.txt    # Python dependencies (now includes gunicorn)
├── static/
│   └── style.css       # Custom styles for dashboard and forms
├── templates/
│   ├── base.html       # Main layout with Navigation Bar
│   ├── index.html      # Landing page / Welcome page
│   ├── login.html      # User Login form
│   ├── signup.html     # User Registration form
│   ├── dashboard.html  # Habit tracking interface
│   ├── reflection.html # Daily mood and win logger
│   └── media.html      # Books & Movies logging with ratings
└── habittracker.db     # SQLite database (Excluded from Git via .gitignore)
```
