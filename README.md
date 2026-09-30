# Kanban Project Manager

A strong, local-first Kanban project management application built with **Python, Streamlit, SQLite, Pandas and Plotly**.

## Features

- Multiple projects / boards
- Kanban workflow: Backlog, To Do, In Progress, Review, Done
- Create, edit, duplicate and delete tasks
- Priority, assignee, labels, due dates and estimates
- Search and advanced filtering
- Dashboard with KPIs and charts
- Project progress and workload analytics
- Task activity history
- SQLite persistence
- CSV and Excel export
- Demo data loader
- Responsive custom styling
- No external database or API required

## Run on Windows

```powershell
cd "Kanban Project Manager"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app opens at:

`http://localhost:8501`

## Project structure

```text
Kanban Project Manager/
├── app.py
├── requirements.txt
├── README.md
└── src/
    ├── __init__.py
    ├── database.py
    ├── services.py
    └── ui.py
```

The SQLite database is automatically created as `kanban.db` in the project folder.
