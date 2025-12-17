# views/dashboard.py (FINAL UNIFIED VERSION)
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from .database import get_list_data, get_data, upsert_attendance, get_attendance_data, delete_attendance

def render_attendance_overview(is_ece=False):
    """Component to show attendance with optional ECE controls."""
    st.subheader("🗓️ Attendance Overview")
    
    # Date Filtering
    col_start, col_end = st.columns(2)
    start_date = col_start.date_input("Filter Start Date", value=datetime.now().date() - timedelta(days=7), key="filter_start")
    end_date = col_end.date_input("Filter End Date", value=datetime.now().date(), key="filter_end")
    
    if start_date > end_date:
        st.error("Start Date must be before End Date.")
        return

    all_att = get_attendance_data()
    if not all_att.empty:
        # Ensure date column is in datetime format for filtering
        all_att['date'] = pd.to_datetime(all_att['date'])
        
        filtered_df = all_att[
            (all_att['date'].dt.date >= start_date) & 
            (all_att['date'].dt.date <= end_date)
        ].sort_values(by=['date', 'child_name'], ascending=[False, True])

        if filtered_df.empty:
            st.info("No records found for this range.")
        else:
            if not is_ece:
                # Simple table view for non-ECE staff
                display_df = filtered_df[['date', 'child_name', 'status', 'logged_by']].copy()
                display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                # Interactive list for ECE (allowing Edit/Delete)
                for _, row in filtered_df.iterrows():
                    rec_id = row['id']
                    date_str = row['date'].strftime('%Y-%m-%d')
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{date_str}** | {row['child_name']} : `{row['status']}`")
                    with c2:
                        # We use two small buttons for Edit and Delete
                        col_e, col_d = st.columns(2)
                        if col_e.button("✏️", key=f"ed_{rec_id}"):
                            st.session_state.edit_attendance_data = row.to_dict()
                            st.rerun()
                        if col_d.button("🗑️", key=f"del_{rec_id}"):
                            delete_attendance(rec_id)
                            st.warning(f"Deleted record for {row['child_name']}")
                            st.rerun()
                    st.divider()

def show_ece_logging_tool():
    """The ECE-only form for logging attendance with improved date handling."""
    st.subheader("📝 Daily Attendance Logging (ECE Only)")
    logged_by = st.session_state.get('username', 'Unknown')
    
    is_edit = 'edit_attendance_data' in st.session_state and st.session_state.edit_attendance_data is not None
    edit_data = st.session_state.get('edit_attendance_data', {})

    # --- FIXED DATE PARSING LOGIC ---
    if is_edit:
        raw_date = edit_data['date']
        # If it's already a date/datetime object, use it; if it's a string, parse it.
        if isinstance(raw_date, str):
            default_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
        elif hasattr(raw_date, 'date'): # Handles datetime objects
            default_date = raw_date.date()
        else:
            default_date = raw_date # Already a date object
    else:
        default_date = datetime.now().date()

    current_date = st.date_input("Log Date", value=default_date)
    
    children_df = get_list_data("children")
    children_list = children_df['child_name'].tolist() if not children_df.empty else []

    if not children_list:
        st.warning("No children found in database. Please add them in Admin Tools.")
        return

    with st.form("ece_logging_form"):
        attendance_options = ["Present", "Absent", "Late", "Cancelled"]
        records = {}
        
        target_children = [edit_data['child_name']] if is_edit else children_list
        if is_edit: 
            st.warning(f"Editing: {edit_data['child_name']}")

        for name in target_children:
            idx = 0
            if is_edit: 
                current_status = edit_data['status']
                if current_status in attendance_options:
                    idx = attendance_options.index(current_status)
            
            records[name] = st.selectbox(f"Status for {name}", attendance_options, index=idx)

        btn_label = "Update Record" if is_edit else "Save Attendance"
        if st.form_submit_button(btn_label, type="primary"):
            for name, status in records.items():
                upsert_attendance(current_date.strftime('%Y-%m-%d'), name, status, logged_by)
            st.session_state.edit_attendance_data = None
            st.success("Attendance Updated." if is_edit else "Attendance Recorded.")
            st.rerun()
    
    if is_edit:
        if st.button("Cancel Edit"):
            st.session_state.edit_attendance_data = None
            st.rerun()

def show_staff_dashboard(role):
    """Dashboard for ECE, OT, SLP, BC, and Admin."""
    st.title(f"📊 {role} Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["📋 Progress Notes", "🗓️ Attendance", "📅 Session Plans"])
    
    with tab1:
        st.header("Recent Clinical Progress")
        df_prog = get_data("progress")
        if not df_prog.empty:
            # Display important columns only
            display_prog = df_prog[['date', 'child_name', 'discipline', 'goal_area', 'status', 'notes', 'author']]
            st.dataframe(display_prog.sort_values(by='date', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No progress notes recorded yet.")

    with tab2:
        # If user is ECE, show the logging form at the top
        if role == 'ECE':
            show_ece_logging_tool()
            st.divider()
        
        # Everyone sees the history list below
        render_attendance_overview(is_ece=(role == 'ECE'))

    with tab3:
        st.header("Daily Session Plans")
        df_plans = get_data("session_plans")
        if not df_plans.empty:
            st.dataframe(df_plans.sort_values(by='date', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No session plans found.")

def show_parent_dashboard(child_name):
    """Simplified Parent view for tracking their specific child."""
    st.title(f"👋 Welcome, {st.session_state.username}")
    st.subheader(f"Attendance & Progress for: {child_name}")
    
    # 1. Attendance Metric
    att = get_attendance_data(child_name=child_name)
    if not att.empty:
        latest = att.iloc[0]
        st.metric(label="Latest Attendance Status", value=latest['status'], delta=f"Recorded on {latest['date']}", delta_color="off")
    
    st.divider()
    
    # 2. Progress Notes Table
    st.subheader("Recent Clinical Updates")
    prog = get_data("progress")
    if not prog.empty:
        child_prog = prog[prog['child_name'] == child_name]
        if not child_prog.empty:
            # Parents don't need to see 'author' or 'media_path' internal data usually, unless specified
            view_df = child_prog[['date', 'discipline', 'goal_area', 'status', 'notes']].sort_values(by='date', ascending=False)
            st.dataframe(view_df, use_container_width=True, hide_index=True)
        else:
            st.info("No progress notes available for your child yet.")
    else:
        st.info("No clinical records found.")

def show_page():
    """Main entry point for the Dashboard page."""
    if not st.session_state.get('logged_in', False):
        st.error("Please log in to view the dashboard.")
        return
        
    role = st.session_state.get('role', '')
    
    if role == 'parent':
        child_link = st.session_state.get('child_link', '')
        if child_link and child_link not in ["All", "None"]:
            show_parent_dashboard(child_link)
        else:
            st.error("Your account is not linked to a specific child profile. Please contact Admin.")
    else:
        # OT, SLP, BC, ECE, and Admin roles
        show_staff_dashboard(role)
