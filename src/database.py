import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta
import random

DB_PATH = Path(__file__).resolve().parent.parent / "kanban.db"

STATUSES = ["Backlog", "To Do", "In Progress", "Review", "Done"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#6366f1',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Backlog',
            priority TEXT NOT NULL DEFAULT 'Medium',
            assignee TEXT DEFAULT 'Unassigned',
            labels TEXT DEFAULT '',
            due_date TEXT,
            estimate REAL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            task_id INTEGER,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_activity_project ON activity(project_id);
        """)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def seed_demo():
    with get_connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] > 0:
            return False

        created = now()
        cur = conn.execute(
            "INSERT INTO projects(name, description, color, created_at, updated_at) VALUES(?,?,?,?,?)",
            ("Product Launch", "Launch the new product experience from discovery to release.", "#6366f1", created, created)
        )
        pid = cur.lastrowid

        demo = [
            ("Research competitor landscape", "Collect competitor features, pricing and positioning.", "Done", "High", "Ananya", "research,market", -3, 5),
            ("Design onboarding flow", "Create the first-time user onboarding experience.", "Review", "High", "Rahul", "design,ux", 2, 8),
            ("Build authentication API", "Implement login, refresh tokens and password reset.", "In Progress", "Critical", "Vikram", "backend,api", 5, 13),
            ("Create dashboard UI", "Build responsive project dashboard components.", "In Progress", "High", "Priya", "frontend,ui", 8, 10),
            ("Write launch documentation", "Prepare user and admin documentation.", "To Do", "Medium", "Ananya", "docs", 12, 4),
            ("Set up CI pipeline", "Add automated tests and deployment checks.", "To Do", "Medium", "Vikram", "devops,ci", 10, 6),
            ("Collect beta feedback", "Interview beta users and categorize feedback.", "Backlog", "Medium", "Rahul", "research", 15, 5),
            ("Release checklist", "Finalize release gates, rollback plan and owners.", "Backlog", "Critical", "Priya", "release", 18, 3),
        ]

        for title, desc, status, priority, assignee, labels, days, estimate in demo:
            due = (date.today() + timedelta(days=days)).isoformat()
            tcur = conn.execute(
                """INSERT INTO tasks
                (project_id,title,description,status,priority,assignee,labels,due_date,estimate,created_at,updated_at,completed_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pid, title, desc, status, priority, assignee, labels, due, estimate, created, created,
                 created if status == "Done" else None)
            )
            tid = tcur.lastrowid
            conn.execute(
                "INSERT INTO activity(project_id,task_id,action,details,created_at) VALUES(?,?,?,?,?)",
                (pid, tid, "Created task", f"{title} added to {status}", created)
            )
        conn.execute(
            "INSERT INTO activity(project_id,action,details,created_at) VALUES(?,?,?,?)",
            (pid, "Created project", "Demo Product Launch project initialized", created)
        )
    return True
