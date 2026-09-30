import io
from datetime import datetime
import pandas as pd
from .database import get_connection, now, STATUSES, PRIORITIES


def list_projects():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM projects ORDER BY updated_at DESC, id DESC", conn
        )


def create_project(name, description, color):
    stamp = now()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO projects(name,description,color,created_at,updated_at) VALUES(?,?,?,?,?)",
            (name.strip(), description.strip(), color, stamp, stamp)
        )
        pid = cur.lastrowid
        conn.execute(
            "INSERT INTO activity(project_id,action,details,created_at) VALUES(?,?,?,?)",
            (pid, "Created project", name.strip(), stamp)
        )
    return pid


def update_project(project_id, name, description, color):
    stamp = now()
    with get_connection() as conn:
        conn.execute(
            "UPDATE projects SET name=?, description=?, color=?, updated_at=? WHERE id=?",
            (name.strip(), description.strip(), color, stamp, project_id)
        )
        conn.execute(
            "INSERT INTO activity(project_id,action,details,created_at) VALUES(?,?,?,?)",
            (project_id, "Updated project", name.strip(), stamp)
        )


def delete_project(project_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM projects WHERE id=?", (project_id,))


def list_tasks(project_id):
    with get_connection() as conn:
        return pd.read_sql_query(
            """SELECT * FROM tasks WHERE project_id=?
               ORDER BY CASE priority
                 WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END,
               COALESCE(due_date,'9999-12-31'), id DESC""",
            conn, params=(project_id,)
        )


def get_task(task_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None


def create_task(project_id, data):
    stamp = now()
    completed = stamp if data["status"] == "Done" else None
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO tasks
            (project_id,title,description,status,priority,assignee,labels,due_date,estimate,created_at,updated_at,completed_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (project_id, data["title"].strip(), data.get("description","").strip(),
             data["status"], data["priority"], data.get("assignee","Unassigned").strip(),
             data.get("labels","").strip(), data.get("due_date") or None,
             float(data.get("estimate",0) or 0), stamp, stamp, completed)
        )
        tid = cur.lastrowid
        conn.execute(
            "INSERT INTO activity(project_id,task_id,action,details,created_at) VALUES(?,?,?,?,?)",
            (project_id, tid, "Created task", f"{data['title']} → {data['status']}", stamp)
        )
        conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (stamp, project_id))
    return tid


def update_task(task_id, data):
    old = get_task(task_id)
    if not old:
        return
    stamp = now()
    completed = stamp if data["status"] == "Done" and old["status"] != "Done" else old["completed_at"]
    if data["status"] != "Done":
        completed = None

    with get_connection() as conn:
        conn.execute(
            """UPDATE tasks SET title=?, description=?, status=?, priority=?, assignee=?,
               labels=?, due_date=?, estimate=?, updated_at=?, completed_at=? WHERE id=?""",
            (data["title"].strip(), data.get("description","").strip(), data["status"],
             data["priority"], data.get("assignee","Unassigned").strip(),
             data.get("labels","").strip(), data.get("due_date") or None,
             float(data.get("estimate",0) or 0), stamp, completed, task_id)
        )
        changes = []
        for key in ["title", "status", "priority", "assignee", "due_date", "estimate"]:
            oldv = old.get(key)
            newv = data.get(key)
            if str(oldv or "") != str(newv or ""):
                changes.append(f"{key}: {oldv or '—'} → {newv or '—'}")
        details = "; ".join(changes) if changes else "Task details updated"
        conn.execute(
            "INSERT INTO activity(project_id,task_id,action,details,created_at) VALUES(?,?,?,?,?)",
            (old["project_id"], task_id, "Updated task", details, stamp)
        )
        conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (stamp, old["project_id"]))


def move_task(task_id, status):
    old = get_task(task_id)
    if not old or status not in STATUSES:
        return
    if old["status"] == status:
        return
    stamp = now()
    completed = stamp if status == "Done" else None
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status=?, updated_at=?, completed_at=? WHERE id=?",
            (status, stamp, completed, task_id)
        )
        conn.execute(
            "INSERT INTO activity(project_id,task_id,action,details,created_at) VALUES(?,?,?,?,?)",
            (old["project_id"], task_id, "Moved task", f"{old['status']} → {status}", stamp)
        )
        conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (stamp, old["project_id"]))


def duplicate_task(task_id):
    old = get_task(task_id)
    if not old:
        return None
    data = old.copy()
    data["title"] = f"{old['title']} (Copy)"
    data["status"] = "Backlog"
    return create_task(old["project_id"], data)


def delete_task(task_id):
    old = get_task(task_id)
    if not old:
        return
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.execute(
            "INSERT INTO activity(project_id,action,details,created_at) VALUES(?,?,?,?)",
            (old["project_id"], "Deleted task", old["title"], now())
        )


def get_activity(project_id, limit=100):
    with get_connection() as conn:
        return pd.read_sql_query(
            """SELECT a.*, t.title AS task_title
               FROM activity a LEFT JOIN tasks t ON t.id=a.task_id
               WHERE a.project_id=? ORDER BY a.created_at DESC LIMIT ?""",
            conn, params=(project_id, limit)
        )


def to_excel(tasks_df, activity_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        tasks_df.to_excel(writer, index=False, sheet_name="Tasks")
        activity_df.to_excel(writer, index=False, sheet_name="Activity")
    output.seek(0)
    return output.getvalue()


def to_csv(tasks_df):
    return tasks_df.to_csv(index=False).encode("utf-8")
