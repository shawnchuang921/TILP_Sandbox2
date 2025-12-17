# views/dashboard.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from .database import get_list_data, get_data, upsert_attendance, get_attendance_data, delete_attendance

def show_page():
    st.title("📊 Program Dashboard")
    
    user_role = st.session_state.get('role', '').lower()
    username = st.session_state.get('username')
    child_link = st.session_state.get('child_link')

    # --- 1. PARENT VIEW ---
    if user_role == 'parent':
        show_parent_dashboard(child_link)
    
    # --- 2. STAFF & ADMIN VIEW ---
    else:
        # --- ROW 1: ATTENDANCE LOGGING (ECE/ADMIN ONLY) ---
        if user_role in ['ece', 'admin']:
            with st.expander("📝 Log Today's Attendance (ECE/Admin Only)", expanded=False):
                with st.form("att_form"):
                    att_date = st.date_input("Date", date.today())
                    child_df = get_list_data("children")
                    if not child_df.empty:
                        selected_child = st.selectbox("Select Child", child_df['child_name'].tolist())
                        status = st.radio("Status", ["Present", "Absent", "Late"], horizontal=True)
                        if st.form_submit_button("Submit Attendance"):
                            upsert_attendance(att_date.isoformat(), selected_child, status, username)
                            st.success(f"Attendance logged for {selected_child}")
                            st.rerun()
        
        # --- ROW 2: DAILY SESSION PLANS ---
        st.subheader("📅 Today's Session Plan")
        df_plans = get_data("session_plans")
        if not df_plans.empty:
            df_plans['date'] = pd.to_datetime(df_plans['date']).dt.date
            today_plan = df_plans[df_plans['date'] == date.today()]
            if not today_plan.empty:
                for _, plan in today_plan.iterrows():
                    st.info(f"**Lead:** {plan['lead_staff']} | **Support:** {plan['support_staff']}")
                    st.write(f"**Learning Block:** {plan['learning_block']}")
            else:
                st.write("No session plan logged for today.")
        
        st.divider()

        # --- ROW 3: ATTENDANCE & PROGRESS OVERVIEW ---
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("📋 Attendance Overview")
            df_att = get_attendance_data()
            if not df_att.empty:
                st.dataframe(df_att[['date', 'child_name', 'status']].head(10), use_container_width=True, hide_index=True)
            else:
                st.write("No attendance records.")

        with col_right:
            st.subheader("📝 Recent Progress Notes")
            df_prog = get_data("progress")
            if not df_prog.empty:
                df_prog = df_prog.sort_values(by='date', ascending=False)
                st.dataframe(df_prog[['date', 'child_name', 'discipline', 'status']].head(10), use_container_width=True, hide_index=True)
            else:
                st.write("No progress notes.")

def show_parent_dashboard(child_link):
    """Encapsulated view for Parents to keep code clean."""
    st.subheader(f"👋 Attendance Overview for {child_link}")
    if not child_link or child_link in ["None", "All"]:
        st.warning("Account not linked to a specific child profile.")
        return

    col1, col2 = st.columns(2)
    start_d = col1.date_input("Start Date", date.today() - timedelta(days=30))
    end_d = col2.date_input("End Date", date.today())

    df_att = get_attendance_data(child_name=child_link)
    if not df_att.empty:
        df_att['date'] = pd.to_datetime(df_att['date']).dt.date
        mask = (df_att['date'] >= start_d) & (df_att['date'] <= end_d)
        df_filtered = df_att.loc[mask]
        
        if not df_filtered.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Present", len(df_filtered[df_filtered['status'] == 'Present']))
            m2.metric("Absent", len(df_filtered[df_filtered['status'] == 'Absent']))
            m3.metric("Late", len(df_filtered[df_filtered['status'] == 'Late']))
            st.table(df_filtered[['date', 'status']].sort_values('date', ascending=False))
        else:
            st.info("No records for selected dates.")
