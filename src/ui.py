import streamlit as st
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .database import STATUSES, PRIORITIES
from .services import (
    list_projects, create_project, update_project, delete_project,
    list_tasks, get_task, create_task, update_task, move_task,
    duplicate_task, delete_task, get_activity, to_excel, to_csv
)

STATUS_ICONS = {
    "Backlog": "📥",
    "To Do": "📝",
    "In Progress": "⚡",
    "Review": "🔍",
    "Done": "✅"
}
PRIORITY_ICONS = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}


def inject_css():
    st.markdown("""
    <style>
    .stApp { background: #f7f8fc; }
    [data-testid="stSidebar"] { background: #111827; }
    [data-testid="stSidebar"] * { color: #f9fafb !important; }
    .brand {
        font-size: 28px; font-weight: 800; letter-spacing: -1px;
        margin-bottom: 4px;
    }
    .subtitle { color: #64748b; margin-bottom: 18px; }
    .hero {
        background: linear-gradient(135deg,#111827 0%,#312e81 100%);
        color: white; border-radius: 18px; padding: 24px 28px; margin-bottom: 20px;
    }
    .hero h1 { margin: 0; font-size: 30px; }
    .hero p { margin: 7px 0 0; color: #dbeafe; }
    .kpi {
        background: white; border: 1px solid #e5e7eb; border-radius: 14px;
        padding: 16px 18px; min-height: 108px;
        box-shadow: 0 2px 10px rgba(15,23,42,.04);
    }
    .kpi-label { color:#64748b; font-size:13px; }
    .kpi-value { font-size:28px; font-weight:800; margin-top:5px; color:#0f172a; }
    .kpi-note { font-size:12px; color:#64748b; margin-top:3px; }
    .kanban-col {
        background:#eef2f7; border:1px solid #e2e8f0; border-radius:14px;
        padding:10px; min-height: 180px;
    }
    .task-card {
        background:white; border:1px solid #e5e7eb; border-radius:12px;
        padding:13px; margin:8px 0; box-shadow:0 2px 6px rgba(15,23,42,.05);
    }
    .task-title { font-weight:700; color:#111827; }
    .task-meta { color:#64748b; font-size:12px; margin-top:7px; }
    .tag {
        display:inline-block; padding:3px 8px; border-radius:999px;
        background:#eef2ff; color:#4338ca; font-size:11px; margin:2px;
    }
    .overdue { color:#dc2626; font-weight:700; }
    .muted { color:#64748b; font-size:13px; }
    div[data-testid="stMetric"] {
        background:white; border:1px solid #e5e7eb; padding:10px 14px; border-radius:14px;
    }
    </style>
    """, unsafe_allow_html=True)


def metric_card(label, value, note=""):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>',
        unsafe_allow_html=True
    )


def task_editor(project_id, task=None, key_prefix="new"):
    editing = task is not None
    with st.form(f"task_form_{key_prefix}"):
        title = st.text_input("Task title *", value=task["title"] if editing else "")
        description = st.text_area("Description", value=task["description"] if editing else "", height=100)
        c1, c2 = st.columns(2)
        status = c1.selectbox("Status", STATUSES, index=STATUSES.index(task["status"]) if editing else 0)
        priority = c2.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(task["priority"]) if editing else 1)
        c3, c4 = st.columns(2)
        assignee = c3.text_input("Assignee", value=task["assignee"] if editing else "Unassigned")
        estimate = c4.number_input("Estimate (hours)", min_value=0.0, step=0.5, value=float(task["estimate"] or 0) if editing else 0.0)
        labels = st.text_input("Labels", value=task["labels"] if editing else "", placeholder="frontend, urgent, api")
        current_due = None
        if editing and task.get("due_date"):
            try:
                current_due = date.fromisoformat(task["due_date"])
            except ValueError:
                pass
        due = st.date_input("Due date", value=current_due)
        submitted = st.form_submit_button("💾 Save task", use_container_width=True)
        if submitted:
            if not title.strip():
                st.error("Task title is required.")
                return False
            data = {
                "title": title, "description": description, "status": status,
                "priority": priority, "assignee": assignee or "Unassigned",
                "estimate": estimate, "labels": labels,
                "due_date": due.isoformat() if due else None
            }
            if editing:
                update_task(task["id"], data)
            else:
                create_task(project_id, data)
            st.success("Task saved.")
            st.rerun()
    return True


def render_board(project_id, tasks):
    st.subheader("Kanban board")
    search = st.text_input("🔎 Search tasks", placeholder="Search title, description, assignee or labels…", key="board_search")
    f1, f2, f3 = st.columns(3)
    priority_filter = f1.multiselect("Priority", PRIORITIES, key="priority_filter")
    assignees = sorted([x for x in tasks["assignee"].dropna().unique() if x])
    assignee_filter = f2.multiselect("Assignee", assignees, key="assignee_filter")
    label_filter = f3.text_input("Label contains", key="label_filter")

    filtered = tasks.copy()
    if search:
        mask = filtered.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]
    if priority_filter:
        filtered = filtered[filtered["priority"].isin(priority_filter)]
    if assignee_filter:
        filtered = filtered[filtered["assignee"].isin(assignee_filter)]
    if label_filter:
        filtered = filtered[filtered["labels"].fillna("").str.contains(label_filter, case=False, na=False)]

    cols = st.columns(len(STATUSES))
    for col, status in zip(cols, STATUSES):
        sdf = filtered[filtered["status"] == status]
        with col:
            st.markdown(
                f'<div class="kanban-col"><b>{STATUS_ICONS[status]} {status}</b>'
                f'<span style="float:right;color:#64748b">{len(sdf)}</span></div>',
                unsafe_allow_html=True
            )
            for _, row in sdf.iterrows():
                due_text = row["due_date"] or "No due date"
                overdue = False
                if row["due_date"] and status != "Done":
                    try:
                        overdue = date.fromisoformat(row["due_date"]) < date.today()
                    except ValueError:
                        pass
                labels = "".join(f'<span class="tag">{x.strip()}</span>' for x in str(row["labels"] or "").split(",") if x.strip())
                st.markdown(
                    f'<div class="task-card"><div class="task-title">{row["title"]}</div>'
                    f'<div class="task-meta">{PRIORITY_ICONS.get(row["priority"],"")} {row["priority"]} · 👤 {row["assignee"]}</div>'
                    f'<div class="task-meta {"overdue" if overdue else ""}">📅 {due_text}</div>'
                    f'<div>{labels}</div></div>',
                    unsafe_allow_html=True
                )
                a, b = st.columns(2)
                if a.button("Open", key=f"open_{row['id']}", use_container_width=True):
                    st.session_state["selected_task"] = int(row["id"])
                    st.rerun()
                if b.button("Move", key=f"move_{row['id']}", use_container_width=True):
                    st.session_state["move_task"] = int(row["id"])
                    st.rerun()


def render_task_detail():
    tid = st.session_state.get("selected_task")
    if not tid:
        return
    task = get_task(tid)
    if not task:
        st.session_state.pop("selected_task", None)
        return
    st.divider()
    st.subheader(f"✏️ Edit task: {task['title']}")
    c1, c2 = st.columns([3,1])
    with c1:
        task_editor(task["project_id"], task, f"edit_{tid}")
    with c2:
        st.markdown("**Task actions**")
        if st.button("📋 Duplicate", use_container_width=True):
            duplicate_task(tid); st.success("Duplicated."); st.rerun()
        if st.button("🗑️ Delete", use_container_width=True):
            delete_task(tid); st.session_state.pop("selected_task", None); st.rerun()
        st.caption("Activity")
        with __import__("contextlib").nullcontext():
            pass
        activity = get_activity(task["project_id"], 50)
        activity = activity[activity["task_id"] == tid]
        if not activity.empty:
            for _, a in activity.head(8).iterrows():
                st.caption(f"{a['created_at']} — {a['action']}")
                st.write(a["details"])


def render_move_dialog():
    tid = st.session_state.get("move_task")
    if not tid:
        return
    task = get_task(tid)
    if not task:
        st.session_state.pop("move_task", None)
        return
    with st.form(f"move_form_{tid}"):
        target = st.selectbox("Move task to", STATUSES, index=STATUSES.index(task["status"]))
        c1, c2 = st.columns(2)
        ok = c1.form_submit_button("Move", use_container_width=True)
        cancel = c2.form_submit_button("Cancel", use_container_width=True)
        if ok:
            move_task(tid, target)
            st.session_state.pop("move_task", None)
            st.rerun()
        if cancel:
            st.session_state.pop("move_task", None)
            st.rerun()


def render_dashboard(tasks):
    total = len(tasks)
    done = int((tasks["status"] == "Done").sum()) if total else 0
    active = total - done
    overdue = 0
    if total:
        due = pd.to_datetime(tasks["due_date"], errors="coerce")
        overdue = int(((due < pd.Timestamp.today().normalize()) & (tasks["status"] != "Done")).sum())
    progress = round(done / total * 100) if total else 0
    hours = float(tasks["estimate"].fillna(0).sum()) if total else 0

    cols = st.columns(5)
    with cols[0]: metric_card("Total tasks", total, "Across this project")
    with cols[1]: metric_card("Completed", done, f"{progress}% completion")
    with cols[2]: metric_card("Active", active, "Not completed")
    with cols[3]: metric_card("Overdue", overdue, "Needs attention")
    with cols[4]: metric_card("Estimated hours", f"{hours:g}", "Planned workload")

    if total:
        c1, c2 = st.columns(2)
        with c1:
            counts = tasks["status"].value_counts().reindex(STATUSES, fill_value=0).reset_index()
            counts.columns = ["Status", "Count"]
            fig = px.bar(counts, x="Status", y="Count", title="Tasks by status", text="Count")
            fig.update_layout(height=330, margin=dict(l=10,r=10,t=55,b=10))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            pr = tasks["priority"].value_counts().reindex(PRIORITIES, fill_value=0).reset_index()
            pr.columns = ["Priority", "Count"]
            fig = px.pie(pr, names="Priority", values="Count", hole=.55, title="Priority mix")
            fig.update_layout(height=330, margin=dict(l=10,r=10,t=55,b=10))
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            assignee = tasks.groupby("assignee", dropna=False).agg(
                Tasks=("id","count"), Hours=("estimate","sum")
            ).reset_index().sort_values("Tasks", ascending=False)
            fig = px.bar(assignee, x="assignee", y="Tasks", title="Workload by assignee", text="Tasks")
            fig.update_layout(height=330, margin=dict(l=10,r=10,t=55,b=10))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            completion = pd.DataFrame({
                "Metric": ["Completed", "Remaining"],
                "Tasks": [done, active]
            })
            fig = go.Figure(go.Pie(labels=completion["Metric"], values=completion["Tasks"], hole=.65))
            fig.update_layout(title="Project completion", height=330, margin=dict(l=10,r=10,t=55,b=10))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tasks yet. Add your first task from the Board tab.")


def render_projects():
    st.subheader("Projects")
    projects = list_projects()
    for _, p in projects.iterrows():
        tasks = list_tasks(int(p["id"]))
        total = len(tasks)
        done = int((tasks["status"] == "Done").sum()) if total else 0
        pct = round(done/total*100) if total else 0
        with st.container(border=True):
            c1, c2, c3 = st.columns([4,2,1])
            c1.markdown(f"### {p['name']}")
            c1.caption(p["description"] or "No description")
            c2.progress(pct/100 if pct else 0, text=f"{pct}% complete · {total} tasks")
            if c3.button("Open", key=f"project_{p['id']}", use_container_width=True):
                st.session_state["project_id"] = int(p["id"])
                st.rerun()


def render_settings(project):
    st.subheader("Project settings")
    with st.form("project_settings"):
        name = st.text_input("Project name", value=project["name"])
        desc = st.text_area("Description", value=project["description"])
        color = st.color_picker("Project color", value=project["color"])
        save = st.form_submit_button("Save changes", use_container_width=True)
        if save:
            update_project(project["id"], name, desc, color)
            st.success("Project updated.")
            st.rerun()

    st.warning("Deleting a project permanently deletes its tasks and activity history.")
    if st.button("Delete project", type="secondary"):
        st.session_state["confirm_delete_project"] = True
    if st.session_state.get("confirm_delete_project"):
        st.error("Are you sure?")
        c1, c2 = st.columns(2)
        if c1.button("Yes, delete permanently", type="primary"):
            delete_project(project["id"])
            st.session_state.pop("confirm_delete_project", None)
            st.session_state.pop("project_id", None)
            st.rerun()
        if c2.button("Cancel"):
            st.session_state.pop("confirm_delete_project", None)
            st.rerun()


def render():
    inject_css()
    projects = list_projects()

    st.sidebar.markdown('<div class="brand">▦ Kanban PM</div><div class="muted">Project command center</div>', unsafe_allow_html=True)
    if st.sidebar.button("＋ New project", use_container_width=True):
        st.session_state["new_project"] = True

    if not projects.empty:
        names = {int(r["id"]): r["name"] for _, r in projects.iterrows()}
        current_id = st.session_state.get("project_id", int(projects.iloc[0]["id"]))
        if current_id not in names:
            current_id = int(projects.iloc[0]["id"])
        selected = st.sidebar.selectbox(
            "Project", list(names.keys()),
            index=list(names.keys()).index(current_id),
            format_func=lambda x: names[x]
        )
        if selected != st.session_state.get("project_id"):
            st.session_state["project_id"] = selected
            st.session_state.pop("selected_task", None)
            st.rerun()

    if st.session_state.get("new_project"):
        st.title("Create project")
        with st.form("new_project_form"):
            name = st.text_input("Project name *", placeholder="e.g. Mobile App Launch")
            desc = st.text_area("Description")
            color = st.color_picker("Color", "#6366f1")
            c1, c2 = st.columns(2)
            submit = c1.form_submit_button("Create project", use_container_width=True)
            cancel = c2.form_submit_button("Cancel", use_container_width=True)
            if submit:
                if not name.strip():
                    st.error("Project name is required.")
                else:
                    pid = create_project(name, desc, color)
                    st.session_state["project_id"] = pid
                    st.session_state.pop("new_project", None)
                    st.rerun()
            if cancel:
                st.session_state.pop("new_project", None)
                st.rerun()
        return

    if projects.empty:
        st.markdown('<div class="hero"><h1>Welcome to Kanban PM</h1><p>Create a project or load demo data to get started.</p></div>', unsafe_allow_html=True)
        if st.button("Create your first project", type="primary"):
            st.session_state["new_project"] = True
            st.rerun()
        return

    project_id = st.session_state.get("project_id", int(projects.iloc[0]["id"]))
    project = projects[projects["id"] == project_id].iloc[0].to_dict()
    tasks = list_tasks(project_id)

    st.markdown(
        f'<div class="hero"><h1>{project["name"]}</h1>'
        f'<p>{project["description"] or "Plan, prioritize and ship work with a focused Kanban workflow."}</p></div>',
        unsafe_allow_html=True
    )

    tabs = st.tabs(["📊 Dashboard", "🗂️ Board", "➕ New task", "📜 Activity", "⚙️ Settings", "📤 Export"])

    with tabs[0]:
        render_dashboard(tasks)

    with tabs[1]:
        render_board(project_id, tasks)
        render_move_dialog()
        render_task_detail()

    with tabs[2]:
        st.subheader("Create task")
        task_editor(project_id)

    with tabs[3]:
        st.subheader("Activity history")
        activity = get_activity(project_id, 200)
        if activity.empty:
            st.info("No activity yet.")
        else:
            for _, a in activity.iterrows():
                task_text = f" · **{a['task_title']}**" if pd.notna(a["task_title"]) else ""
                st.markdown(f"**{a['action']}**{task_text}  \n{a['details']}  \n<small>{a['created_at']}</small>", unsafe_allow_html=True)
                st.divider()

    with tabs[4]:
        render_settings(project)

    with tabs[5]:
        st.subheader("Export project data")
        st.caption("Exports include the current project's tasks and activity history.")
        activity = get_activity(project_id, 1000)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Download CSV", data=to_csv(tasks), file_name=f"{project['name'].replace(' ','_')}_tasks.csv", mime="text/csv", use_container_width=True)
        with c2:
            st.download_button("⬇️ Download Excel", data=to_excel(tasks, activity), file_name=f"{project['name'].replace(' ','_')}_project.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.sidebar.divider()
    st.sidebar.caption("Data is stored locally in SQLite.")
