# views/tracker.py
import streamlit as st
import pandas as pd
from datetime import date
from .database import get_list_data, save_progress

def show_page():
    st.title("📝 Progress Tracker")
    username = st.session_state.get("username", "Staff")

    # Use a form to group inputs
    with st.form("progress_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d_date = c1.date_input("Date", date.today())
        
        children = get_list_data("children")['child_name'].tolist()
        disciplines = get_list_data("disciplines")['name'].tolist()
        goals = get_list_data("goal_areas")['name'].tolist()
        
        selected_child = c1.selectbox("Child", children)
        selected_disc = c2.selectbox("Discipline", disciplines)
        selected_goal = c1.selectbox("Goal Area", goals)
        status = c2.selectbox("Status", ["Mastered", "Progressing", "Emerging", "Regression", "Not Observed"])
        
        clinical_notes = st.text_area("🔒 Clinical Notes (Internal)")
        parent_notes = st.text_area("👨‍👩‍👧 Note to Parents (Visible on Portal)")
        media_url = st.text_input("Media Link (Optional)")

        if st.form_submit_button("Save Entry"):
            save_progress(d_date, selected_child, selected_disc, selected_goal, status, clinical_notes, media_url, username, parent_notes)
            st.success("Progress Saved! Form cleared for next entry.")
