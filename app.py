import streamlit as st
from src.database import init_db, seed_demo
from src.ui import render

st.set_page_config(
    page_title="Kanban Project Manager",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

if "seeded" not in st.session_state:
    st.session_state["seeded"] = False

# Small first-run helper
if not st.session_state["seeded"]:
    from src.services import list_projects
    if list_projects().empty:
        st.sidebar.info("New installation detected.")
        if st.sidebar.button("Load demo project", use_container_width=True):
            seed_demo()
            st.session_state["seeded"] = True
            st.rerun()

render()
