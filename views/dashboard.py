# views/dashboard.py (FINAL VERSION - Added ECE Edit/Delete Attendance)
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from .database import get_list_data, get_data, upsert_attendance, get_attendance_data, delete_attendance

def show_ece_attendance_dashboard():
    """Attendance logging interface for ECE role."""
    st.title("📊 ECE Attendance Tracker")
    st.markdown("---")

    logged_by = st.session_state.get('username', 'Unknown')
    
    # --- 1. ATTENDANCE LOGGING / EDIT FORM ---
    
    # Check for Edit Mode
    is_edit_mode = 'edit_attendance_data' in st.session_state and st.session_state.edit_attendance_data is not None
    edit_data = st.session_state.get('edit_attendance_data', {})

    st.subheader("Daily Attendance Logging")

    # Determine default date based on whether we are editing or creating new
    if is_edit_mode and 'date' in edit_data:
        try:
            default_date_value = datetime.strptime(edit_data['date'], '%Y-%m-%d').date()
        except:
            default_date_value = datetime.now().date()
    else:
        default_date_value = datetime.now().date()
    
    # Allow ECE to select ANY date (no default value forces a selection)
    current_date = st.date_input("Select Date for Attendance", value=default_date_value)
    current_date_str = current_date.strftime('%Y-%m-%d')

    # Get all children
    children_df = get_list_data("children")
    children_list = children_df['child_name'].tolist()

    if not children_list:
        st.info("No child profiles found in the database. Please add children in Admin Tools.")
        return

    # Get existing attendance for the selected date OR the single record if editing
    if is_edit_mode:
        existing_attendance = pd.DataFrame([edit_data])
    else:
        existing_attendance = get_attendance_data(date=current_date_str)
    
    st.caption(f"Review/Set status for **{current_date_str}**")

    # Set default child for editing
    if is_edit_mode and edit_data.get('child_name') in children_list:
        child_index = children_list.index(edit_data.get('child_name'))
        # In edit mode, we only show the child being edited
        current_child_list = [edit_data['child_name']]
        is_child_disabled = True
    else:
        child_index = 0
        current_child_list = children_list
        is_child_disabled = False


    with st.form("attendance_form"):
        attendance_options = ["Present", "Absent", "Late", "Cancelled"]
        attendance_records = {}

        if is_edit_mode:
            st.warning(f"Editing attendance for **{edit_data['child_name']}**")
        
        # Display each child with their current status
        for child_name in current_child_list:
            
            # --- Child Name Selector ---
            child_selectbox = st.selectbox(
                "Child Name",
                children_list,
                index=children_list.index(child_name),
                key=f"child_sel_{child_name}",
                disabled=is_child_disabled
            )
            
            # --- Status Selector ---
            default_status = "Absent" 
            if not existing_attendance.empty:
                current_record = existing_attendance[existing_attendance['child_name'] == child_name]
                if not current_record.empty:
                    default_status = current_record['status'].iloc[0]

            attendance_records[child_name] = st.selectbox(
                f"Status for **{child_name}**",
                attendance_options,
                index=attendance_options.index(default_status),
                key=f"status_{child_name}_{current_date_str}" 
            )

        st.markdown("---")
        
        col_save, col_cancel = st.columns(2)

        if col_save.form_submit_button("✅ Save Daily Attendance / Update Record", type="primary"):
            for child, status in attendance_records.items():
                if status:
                    upsert_attendance(current_date_str, child, status, logged_by)
            st.success(f"Attendance for {current_date_str} saved/updated by {logged_by}.")
            st.session_state.edit_attendance_data = None
            st.rerun()

        if is_edit_mode and col_cancel.form_submit_button("❌ Cancel Edit"):
            st.session_state.edit_attendance_data = None
            st.rerun()


    st.markdown("---")

    # --- 2. HISTORICAL ATTENDANCE FILTER & MODIFICATION ---
    st.subheader("Attendance Overview")
    
    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=7)
    
    col_start, col_end = st.columns(2)
    start_date = col_start.date_input("Start Date", value=default_start, key="ece_start_date")
    end_date = col_end.date_input("End Date", value=default_end, key="ece_end_date")
    
    if start_date > end_date:
        st.error("Error: Start Date must be before or the same as the End Date.")
        return

    # Fetch all data 
    all_attendance_df = get_attendance_data() 
    
    if all_attendance_df.empty:
        st.info("No historical attendance data found.")
        return

    all_attendance_df['date'] = pd.to_datetime(all_attendance_df['date'])
    
    # Filter by selected date range
    filtered_df = all_attendance_df[
        (all_attendance_df['date'].dt.date >= start_date) & 
        (all_attendance_df['date'].dt.date <= end_date)
    ].sort_values(by=['date', 'child_name'], ascending=[False, True])
    
    
    if filtered_df.empty:
        st.info(f"No attendance records found between {start_date} and {end_date}.")
    else:
        
        for index, row in filtered_df.iterrows():
            record_id = row['id']
            # Format the date back to string for cleaner display
            display_date = row['date'].strftime('%Y-%m-%d')

            col_disp, col_action = st.columns([4, 1])

            with col_disp:
                st.markdown(f"**{display_date}** | **{row['child_name']}** - Status: **{row['status']}** (Logged by: {row['logged_by']})")
            
            with col_action:
                c_edit, c_del = st.columns(2)
                
                # EDIT BUTTON - triggers edit mode
                if c_edit.button("✏️ Edit", key=f"edit_att_{record_id}"):
                    st.session_state.edit_attendance_data = row.to_dict() # Store the data to be edited
                    st.rerun() 
                
                # DELETE BUTTON - triggers confirmation
                if c_del.button("🗑️", key=f"del_att_btn_{record_id}"):
                    st.session_state[f"confirm_att_del_{record_id}"] = True
                    st.rerun()

                # Confirmation Box for Delete
                if st.session_state.get(f"confirm_att_del_{record_id}", False):
                    st.warning("Confirm delete?")
                    conf_c1, conf_c2 = st.columns(2)
                    with conf_c1:
                        if st.button("Yes, Delete", key=f"yes_att_del_{record_id}"):
                            delete_attendance(record_id)
                            st.success("Record deleted!")
                            del st.session_state[f"confirm_att_del_{record_id}"]
                            st.rerun()
                    with conf_c2:
                        if st.button("Cancel", key=f"no_att_del_{record_id}"):
                            del st.session_state[f"confirm_att_del_{record_id}"]
                            st.rerun()
            
            st.markdown("---") # Separator between records


def show_parent_dashboard(child_name_link):
    # ... (Parent Dashboard remains unchanged from the previous step)
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
    
    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=30)
    
    col_start, col_end = st.columns(2)
    p_start_date = col_start.date_input("Start Date", value=default_start, key="p_start_date")
    p_end_date = col_end.date_input("End Date", value=default_end, key="p_end_date")
    
    if p_start_date > p_end_date:
        st.error("Error: Start Date must be before or the same as the End Date.")
        return

    child_attendance_df = get_attendance_data(child_name=child_name_link)
    
    if child_attendance_df.empty:
        st.info(f"No attendance history found for {child_name_link}.")
        return

    child_attendance_df['date'] = pd.to_datetime(child_attendance_df['date'])
    
    parent_filtered_df = child_attendance_df[
        (child_attendance_df['date'].dt.date >= p_start_date) & 
        (child_attendance_df['date'].dt.date <= p_end_date)
    ].sort_values(by='date', ascending=False)
    
    
    if parent_filtered_df.empty:
        st.info(f"No attendance records found for {child_name_link} between {p_start_date} and {p_end_date}.")
    else:
        parent_filtered_df['date'] = parent_filtered_df['date'].dt.strftime('%Y-%m-%d')
        
        display_df = parent_filtered_df[['date', 'status']]
        display_df.columns = ["Date", "Status"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


    st.markdown("---")
    
    # 3. Display Latest Progress Notes
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
