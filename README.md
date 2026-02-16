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

## Project Structure

```
habittracker/
├── app.py           # Flask app and routes
├── requirements.txt # Python dependencies
├── static/
│   └── style.css    # Minimal CSS
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   └── reflection.html
└── habittracker.db  # SQLite database (created on first run)
```
