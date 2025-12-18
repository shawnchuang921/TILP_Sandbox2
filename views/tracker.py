# views/tracker.py
# (Keep imports same)
import streamlit as st
import pandas as pd
from datetime import date
from .database import get_list_data, save_progress, get_data

def show_page():
    st.title("📝 Progress Tracker")
    
    # ... (Keep existing role checks) ...
    username = st.session_state.get("username", "Staff")

    with st.form("progress_form"):
        # ... (Keep date, child, discipline, goal selectors same as before) ...
        c1, c2 = st.columns(2)
        d_date = c1.date_input("Date", date.today())
        
        # Load lists
        children = get_list_data("children")['child_name'].tolist()
        disciplines = get_list_data("disciplines")['name'].tolist()
        goals = get_list_data("goal_areas")['name'].tolist()
        
        selected_child = c1.selectbox("Child", children)
        selected_disc = c2.selectbox("Discipline", disciplines)
        selected_goal = c1.selectbox("Goal Area", goals)
        status = c2.selectbox("Status", ["Mastered", "Progressing", "Emerging", "Regression", "Not Observed"])
        
        clinical_notes = st.text_area("🔒 Clinical Notes (Internal)")
        
        # --- NEW FIELD ---
        parent_notes = st.text_area("👨‍👩‍👧 Note to Parents (Visible on Portal)", placeholder="Great job today! Please practice...")
        # -----------------
        
        media_url = st.text_input("Media Link (Optional)")

        if st.form_submit_button("Save Entry"):
            # Update function call to include parent_notes
            save_progress(d_date, selected_child, selected_disc, selected_goal, status, clinical_notes, media_url, username, parent_notes)
            st.success("Saved!")
    
    # (Existing history view code can remain, ensure it gets the new columns if you display them)
