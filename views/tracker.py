# views/tracker.py
import streamlit as st
import pandas as pd
from datetime import date
from .database import get_list_data, save_progress, get_data, delete_progress

def show_page():
    st.title("📝 Progress Tracker")
    
    # Check permissions
    role = st.session_state.get('role', '').lower()
    username = st.session_state.get('username', 'Staff')
    
    staff_roles = ["admin", "ot", "slp", "bc", "ece", "assistant", "staff", "therapist"]
    if role not in staff_roles:
        st.error("Access Restricted: This page is for staff documentation only.")
        return

    # --- SECTION 1: DOCUMENT PROGRESS ---
    st.subheader("New Progress Entry")
    
    # Using a form with clear_on_submit=True to make messages/notes disappear after saving
    with st.form("progress_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        # Date and Child Selection
        d_date = c1.date_input("Date of Session", date.today())
        
        # Fetching dynamic list data from database
        children_df = get_list_data("children")
        children = children_df['child_name'].tolist() if not children_df.empty else []
        
        disciplines_df = get_list_data("disciplines")
        disciplines = disciplines_df['name'].tolist() if not disciplines_df.empty else []
        
        goals_df = get_list_data("goal_areas")
        goals = goals_df['name'].tolist() if not goals_df.empty else []
        
        selected_child = c1.selectbox("Child", children)
        selected_disc = c2.selectbox("Discipline", disciplines)
        selected_goal = c1.selectbox("Goal Area", goals)
        
        status = c2.selectbox("Status", [
            "Progressing", 
            "Mastered", 
            "Emerging", 
            "Regression", 
            "Not Observed"
        ])
        
        st.divider()
        
        # Input Areas
        clinical_notes = st.text_area(
            "🔒 Clinical Notes (Internal Only)", 
            placeholder="Detailed clinical observations, data points, and internal staff notes..."
        )
        
        parent_notes = st.text_area(
            "👨‍👩‍👧 Note to Parents", 
            placeholder="Recommendations, homework, or encouraging updates to share with the family..."
        )
        
        media_url = st.text_input("Media Link (Optional)", placeholder="Link to Google Drive photo/video")

        submit_btn = st.form_submit_button("Save Progress Entry")
        
        if submit_btn:
            if not selected_child or not selected_disc:
                st.error("Please select both a Child and a Discipline.")
            else:
                save_progress(
                    d_date, 
                    selected_child, 
                    selected_disc, 
                    selected_goal, 
                    status, 
                    clinical_notes, 
                    media_url, 
                    username, 
                    parent_notes
                )
                st.success(f"Successfully logged progress for {selected_child}! The form has been cleared.")

    st.divider()

    # --- SECTION 2: RECENT HISTORY & FEEDBACK REVIEW ---
    st.subheader("📜 Recent Documentation History")
    
    # Load all progress data
    df = get_data("progress")
    
    if not df.empty:
        # Sorting by most recent
        df = df.sort_values('id', ascending=False)
        
        # Optional Filter
        filter_child = st.selectbox("Filter History by Child:", ["All"] + children)
        if filter_child != "All":
            df = df[df['child_name'] == filter_child]

        for index, row in df.head(20).iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                
                col1.markdown(f"**{row['child_name']}** | {row['discipline']} - {row['goal_area']}")
                col1.caption(f"Date: {row['date']} | Author: {row['author']}")
                
                # Visual Status
                status_color = "green" if row['status'] == "Mastered" else "blue"
                col2.markdown(f":{status_color}[**{row['status']}**]")
                
                with st.expander("View Full Note & Parent Feedback"):
                    st.markdown("**🔒 Internal Clinical Notes:**")
                    st.write(row['notes'])
                    
                    if row.get('parent_note'):
                        st.success(f"**Note Sent to Parent:**\n{row['parent_note']}")
                    
                    # Reflection of Parent Feedback (New Functionality)
                    if row.get('parent_feedback'):
                        st.warning(f"💬 **Parent Feedback Received:**\n{row['parent_feedback']}")
                    else:
                        st.info("No feedback received from parent yet.")
                    
                    if row['media_path']:
                        st.markdown(f"[🔗 View Media]({row['media_path']})")
                    
                    # Delete option for Admins or Authors
                    if role == "admin" or username == row['author']:
                        if st.button("Delete Entry", key=f"del_{row['id']}"):
                            delete_progress(row['id'])
                            st.rerun()
    else:
        st.info("No progress entries found in the database.")
