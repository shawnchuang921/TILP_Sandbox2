# views/dashboard.py (FINAL VERSION - Flexible ECE Attendance & Filtering)
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from .database import get_list_data, get_data, upsert_attendance, get_attendance_data

def show_ece_attendance_dashboard():
    """Attendance logging interface for ECE role."""
    st.title("📊 ECE Attendance Tracker")
    st.markdown("---")

    logged_by = st.session_state.get('username', 'Unknown')
    
    # --- 1. ATTENDANCE LOGGING FORM ---
    st.subheader("Daily Attendance Logging")

    # Change 1: Allow ECE to select ANY date (no default value)
    current_date = st.date_input("Select Date for Attendance")
    current_date_str = current_date.strftime('%Y-%m-%d') if current_date else datetime.now().strftime('%Y-%m-%d')

    # Get all children
    children_df = get_list_data("children")
    children_list = children_df['child_name'].tolist()

    if not children_list:
        st.info("No child profiles found in the database. Please add children in Admin Tools.")
        return

    # Get existing attendance for the selected date
    existing_attendance = get_attendance_data(date=current_date_str)
    
    st.caption(f"Review/Set status for **{current_date_str}**")

    with st.form("attendance_form"):
        attendance_options = ["Present", "Absent", "Late", "Cancelled"]
        
        attendance_records = {}
        
        # Display each child with their current status
        for child_name in children_list:
            default_status = "Absent" 
            if not existing_attendance.empty:
                current_record = existing_attendance[existing_attendance['child_name'] == child_name]
                if not current_record.empty:
                    default_status = current_record['status'].iloc[0]

            # Use a unique key for each selectbox
            attendance_records[child_name] = st.selectbox(
                f"Status for **{child_name}**",
                attendance_options,
                index=attendance_options.index(default_status),
                key=f"status_{child_name}_{current_date_str}" # Key updated to prevent conflict across dates
            )

        st.markdown("---")
        if st.form_submit_button("✅ Save Daily Attendance", type="primary"):
            for child, status in attendance_records.items():
                if status:
                    upsert_attendance(current_date_str, child, status, logged_by)
            st.success(f"Attendance for {current_date_str} saved by {logged_by}.")
            st.rerun()

    st.markdown("---")

    # --- 2. HISTORICAL ATTENDANCE FILTER ---
    st.subheader("Attendance Overview")
    
    # Set default date range for filter (e.g., last 7 days)
    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=7)
    
    col_start, col_end = st.columns(2)
    start_date = col_start.date_input("Start Date", value=default_start)
    end_date = col_end.date_input("End Date", value=default_end)
    
    if start_date > end_date:
        st.error("Error: Start Date must be before or the same as the End Date.")
        return

    # Fetch all data within the date range
    all_attendance_df = get_attendance_data() 
    
    if all_attendance_df.empty:
        st.info("No historical attendance data found.")
        return

    # Convert date column to datetime for filtering
    all_attendance_df['date'] = pd.to_datetime(all_attendance_df['date'])
    
    # Filter by selected date range
    filtered_df = all_attendance_df[
        (all_attendance_df['date'].dt.date >= start_date) & 
        (all_attendance_df['date'].dt.date <= end_date)
    ].sort_values(by=['date', 'child_name'], ascending=[False, True])
    
    
    if filtered_df.empty:
        st.info(f"No attendance records found between {start_date} and {end_date}.")
    else:
        # Format the date back to string for cleaner display
        filtered_df['date'] = filtered_df['date'].dt.strftime('%Y-%m-%d')
        
        # Select and rename columns for display
        display_df = filtered_df[['date', 'child_name', 'status', 'logged_by']]
        display_df.columns = ["Date", "Child Name", "Status", "Logged By"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


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

    # 2. Parent Historical Attendance Filter
    st.header("Attendance History")
    
    # Set default date range for filter (e.g., last 30 days)
    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=30)
    
    col_start, col_end = st.columns(2)
    p_start_date = col_start.date_input("Start Date", value=default_start, key="p_start_date")
    p_end_date = col_end.date_input("End Date", value=default_end, key="p_end_date")
    
    if p_start_date > p_end_date:
        st.error("Error: Start Date must be before or the same as the End Date.")
        return

    # Fetch data only for the linked child
    child_attendance_df = get_attendance_data(child_name=child_name_link)
    
    if child_attendance_df.empty:
        st.info(f"No attendance history found for {child_name_link}.")
        return

    # Convert date column to datetime for filtering
    child_attendance_df['date'] = pd.to_datetime(child_attendance_df['date'])
    
    # Filter by selected date range
    parent_filtered_df = child_attendance_df[
        (child_attendance_df['date'].dt.date >= p_start_date) & 
        (child_attendance_df['date'].dt.date <= p_end_date)
    ].sort_values(by='date', ascending=False)
    
    
    if parent_filtered_df.empty:
        st.info(f"No attendance records found for {child_name_link} between {p_start_date} and {p_end_date}.")
    else:
        # Format the date back to string for cleaner display
        parent_filtered_df['date'] = parent_filtered_df['date'].dt.strftime('%Y-%m-%d')
        
        # Select and rename columns for display
        display_df = parent_filtered_df[['date', 'status']]
        display_df.columns = ["Date", "Status"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


    st.markdown("---")
    
    # 3. Display Latest Progress Notes (Example - keep this section simple for now)
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
    """Dashboard view for all other Staff/Admin roles."""
    st.title("📊 Program Dashboard & Reports (Staff View)")
    st.info("Coming Soon: Comprehensive program overview and custom reporting tools.")
    st.markdown("---")

# --- ENTRY POINT FUNCTION ---

def show_page():
    """Wrapper function called by app.py to display the correct dashboard based on role."""
    if not st.session_state.get('logged_in', False):
        st.error("Please log in to access the Dashboard.")
        return
        
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
