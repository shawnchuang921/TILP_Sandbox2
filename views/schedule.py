# views/schedule.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from .database import get_appointments, create_appointment, get_list_data, update_appointment, delete_appointment

def show_page():
    st.title("🗓️ Schedule & Appointments")
    
    role = st.session_state.get('role', '').lower()
    child_link = st.session_state.get('child_link')

    # --- ADMIN VIEW: Create & Manage ---
    if role == 'admin':
        col_c, col_m = st.columns(2)
        
        # 1. Create
        with col_c.expander("➕ Book Appointment", expanded=False):
            with st.form("appt_form"):
                d_col, t_col = st.columns(2)
                a_date = d_col.date_input("Date", date.today())
                a_time = t_col.time_input("Time", datetime.now().time())
                
                child_df = get_list_data("children")
                children = child_df['child_name'].tolist() if not child_df.empty else []
                s_child = st.selectbox("Child", children)
                
                d_type = st.selectbox("Type", ["OT Session", "SLP Session", "BC Consultation", "Assessment", "Other"])
                staff = st.text_input("Provider Name")
                cost = st.number_input("Cost ($)", value=0.0)
                
                if st.form_submit_button("Book"):
                    create_appointment(a_date, str(a_time), s_child, d_type, staff, cost, "Scheduled")
                    st.success("Booked!")
                    st.rerun()

        # 2. Manage
        with col_m.expander("🛠️ Manage Appointments", expanded=False):
            st.info("Refer to the 'ID' in the table below.")
            appt_id = st.number_input("Appointment ID", min_value=1, step=1)
            action = st.radio("Action", ["Modify details", "Delete"], horizontal=True)
            
            if action == "Modify details":
                new_date = st.date_input("New Date", date.today(), key="mod_date")
                new_time = st.time_input("New Time", datetime.now().time(), key="mod_time")
                new_stat = st.selectbox("Status", ["Scheduled", "Completed", "Cancelled", "No Show"])
                if st.button("Update Appointment"):
                    update_appointment(appt_id, new_date, str(new_time), new_stat)
                    st.success("Updated!")
                    st.rerun()
            else:
                if st.button("🗑️ Delete Permanently", type="primary"):
                    delete_appointment(appt_id)
                    st.warning("Deleted.")
                    st.rerun()
        st.divider()

    # --- PARENT/LIST VIEW ---
    df = pd.DataFrame()

    if role == 'parent':
        if child_link and child_link not in ["None", "All"]:
            df = get_appointments(child_name=child_link)
            st.subheader(f"Upcoming Schedule for {child_link}")
        else:
            st.error("No child linked.")
    elif role == 'admin':
        df = get_appointments()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Display ID for Admin convenience
        display_cols = ['date', 'time', 'child_name', 'discipline', 'staff', 'cost', 'status']
        if role == 'admin':
            display_cols.insert(0, 'id')
            
        # Separate Past vs Upcoming
        today = date.today()
        upcoming = df[df['date'] >= today].sort_values('date')
        past = df[df['date'] < today].sort_values('date', ascending=False)
        
        tab1, tab2 = st.tabs(["📅 Upcoming", "📜 Past History"])
        
        with tab1:
            if not upcoming.empty:
                st.dataframe(upcoming[display_cols], use_container_width=True, hide_index=True)
            else:
                st.info("No upcoming appointments.")

        with tab2:
            st.dataframe(past[display_cols], use_container_width=True, hide_index=True)
            
    else:
        st.info("No appointments found.")
