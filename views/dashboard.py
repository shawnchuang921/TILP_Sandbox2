# views/dashboard.py (COMPLETE REPLACEMENT - Introducing ECE Attendance)
import streamlit as st
import pandas as pd
from datetime import datetime
from .database import get_list_data, get_data, upsert_attendance, get_attendance_data

def show_ece_attendance_dashboard():
    """Attendance logging interface for ECE role."""
    st.title("📊 ECE Attendance Tracker")
    st.markdown("---")

    current_date = st.date_input("Select Date for Attendance", value=datetime.now().date())
    current_date_str = current_date.strftime('%Y-%m-%d')
    logged_by = st.session_state.get('username', 'Unknown')

    # Get all children
    children_df = get_list_data("children")
    children_list = children_df['child_name'].tolist()

    if not children_list:
        st.info("No child profiles found in the database. Please add children in Admin Tools.")
        return

    # Get existing attendance for the selected date
    existing_attendance = get_attendance_data(date=current_date_str)
    
    st.subheader(f"Attendance for {current_date_str}")

    with st.form("attendance_form"):
        attendance_options = ["Present", "Absent", "Late", "Cancelled"]
        
        # Display each child with their current status
        attendance_records = {}
        for child_name in children_list:
            default_status = "Absent" # Default status if no record exists
            if not existing_attendance.empty:
                current_record = existing_attendance[existing_attendance['child_name'] == child_name]
                if not current_record.empty:
                    default_status = current_record['status'].iloc[0]

            # Use a unique key for each selectbox
            attendance_records[child_name] = st.selectbox(
                f"Status for **{child_name}**",
                attendance_options,
                index=attendance_options.index(default_status),
                key=f"status_{child_name}"
            )

        st.markdown("---")
        if st.form_submit_button("✅ Save Daily Attendance", type="primary"):
            for child, status in attendance_records.items():
                if status:
                    upsert_attendance(current_date_str, child, status, logged_by)
            st.success(f"Attendance for {current_date_str} saved by {logged_by}.")
            st.rerun()

def show_parent_dashboard(child_name_link):
    """Dashboard view for a Parent role."""
    st.title(f"📊 Dashboard for {child_name_link}")
    st.markdown("---")

    # 1. Display Latest Attendance Status
    st.header("Daily Check-In Status")
    
    latest_attendance = get_attendance_data(child_name=child_name_link)
    
    if not latest_attendance.empty:
        latest_record = latest_attendance.iloc[0]
        st.metric(
            label="Latest Attendance Status", 
            value=latest_record['status'], 
            delta=f"Date: {latest_record['date']}",
            delta_color="off"
        )
    else:
        st.info(f"No attendance records found for {child_name_link}.")

    st.markdown("---")
    
    # 2. Display Latest Progress Notes (Example - keep this section simple for now)
    st.header("Latest Progress Notes")
    
    progress_df = get_data("progress")
    child_progress = progress_df[progress_df['child_name'] == child_name_link]
    
    if not child_progress.empty:
        latest_note = child_progress.sort_values(by='date', ascending=False).iloc[0]
        st.info(f"**Last Log Date:** {latest_note['date']} | **Discipline:** {latest_note['discipline']}")
        st.write(latest_note['notes'])
    else:
        st.info(f"No progress notes found for {child_name_link}.")


def show_staff_dashboard():
    """Dashboard view for all other Staff/Admin roles (excluding ECE)."""
    st.title("📊 Program Dashboard & Reports (Staff View)")
    st.info("Coming Soon: Comprehensive program overview and custom reporting tools.")
    st.markdown("---")
    # You would build summary tables and charts here

# --- ENTRY POINT FUNCTION ---

def show_page():
    """Wrapper function called by app.py to display the correct dashboard based on role."""
    user_role = st.session_state.get('role', '')

    if user_role == 'parent':
        child_name_link = st.session_state.get('child_link', 'Child Not Linked')
        if child_name_link == 'All' or child_name_link == 'None':
            st.error("Your parent account is not linked to a child. Please contact your administrator.")
        else:
            show_parent_dashboard(child_name_link)

    elif user_role == 'ECE':
        show_ece_attendance_dashboard()
        
    else:
        # All other staff roles (Admin, OT, SLP, etc.)
        show_staff_dashboard()
