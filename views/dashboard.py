# views/dashboard.py (RESTORING STAFF VIEW)
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from .database import get_list_data, get_data, upsert_attendance, get_attendance_data, delete_attendance

def show_ece_attendance_dashboard():
    """Attendance logging interface for ECE role."""
    st.title("📊 ECE Attendance Tracker")
    st.markdown("---")
    logged_by = st.session_state.get('username', 'Unknown')
    
    is_edit_mode = 'edit_attendance_data' in st.session_state and st.session_state.edit_attendance_data is not None
    edit_data = st.session_state.get('edit_attendance_data', {})

    st.subheader("Daily Attendance Logging")
    default_date_value = datetime.strptime(edit_data['date'], '%Y-%m-%d').date() if is_edit_mode else datetime.now().date()
    current_date = st.date_input("Select Date for Attendance", value=default_date_value)
    current_date_str = current_date.strftime('%Y-%m-%d')

    children_df = get_list_data("children")
    children_list = children_df['child_name'].tolist() if not children_df.empty else []

    if not children_list:
        st.info("No child profiles found.")
        return

    existing_attendance = pd.DataFrame([edit_data]) if is_edit_mode else get_attendance_data(date=current_date_str)
    
    with st.form("attendance_form"):
        attendance_options = ["Present", "Absent", "Late", "Cancelled"]
        attendance_records = {}
        current_child_list = [edit_data['child_name']] if is_edit_mode else children_list
        
        for child_name in current_child_list:
            default_status = "Absent" 
            if not existing_attendance.empty:
                current_record = existing_attendance[existing_attendance['child_name'] == child_name]
                if not current_record.empty:
                    default_status = current_record['status'].iloc[0]

            attendance_records[child_name] = st.selectbox(f"Status for **{child_name}**", attendance_options, index=attendance_options.index(default_status))

        if st.form_submit_button("✅ Save/Update Attendance"):
            for child, status in attendance_records.items():
                upsert_attendance(current_date_str, child, status, logged_by)
            st.session_state.edit_attendance_data = None
            st.rerun()

    st.markdown("---")
    st.subheader("Attendance Overview")
    all_att = get_attendance_data()
    if not all_att.empty:
        all_att['date'] = pd.to_datetime(all_att['date'])
        st.dataframe(all_att.sort_values(by='date', ascending=False), use_container_width=True, hide_index=True)

def show_parent_dashboard(child_name_link):
    st.title(f"📊 Dashboard for {child_name_link}")
    latest_attendance = get_attendance_data(child_name=child_name_link)
    if not latest_attendance.empty:
        st.metric("Latest Status", latest_attendance.iloc[0]['status'], delta=latest_attendance.iloc[0]['date'])
    
    st.markdown("---")
    st.subheader("Recent Progress")
    prog = get_data("progress")
    child_prog = prog[prog['child_name'] == child_name_link] if not prog.empty else pd.DataFrame()
    st.dataframe(child_prog.sort_values(by='date', ascending=False).head(5), use_container_width=True)

def show_staff_dashboard():
    st.title("📊 Program Overview Dashboard")
    df_prog = get_data("progress")
    df_plans = get_data("session_plans")
    
    col1, col2 = st.columns(2)
    col1.metric("Clinical Notes", len(df_prog))
    col2.metric("Session Plans", len(df_plans))
    
    st.subheader("Recent Activity")
    st.dataframe(df_prog.sort_values(by='date', ascending=False).head(10), use_container_width=True)

def show_page():
    user_role = st.session_state.get('role', '')
    if user_role == 'parent':
        show_parent_dashboard(st.session_state.get('child_link', ''))
    elif user_role == 'ECE':
        show_ece_attendance_dashboard()
    else:
        show_staff_dashboard()
