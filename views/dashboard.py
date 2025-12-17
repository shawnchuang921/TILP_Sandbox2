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
        return

    # --- 2. STAFF & ADMIN VIEW ---
    
    # --- SECTION A: TODAY'S FULL SESSION PLAN ---
    st.subheader("📅 Today's Full Session Plan")
    df_plans = get_data("session_plans")
    if not df_plans.empty:
        df_plans['date'] = pd.to_datetime(df_plans['date']).dt.date
        today_plan = df_plans[df_plans['date'] == date.today()]
        
        if not today_plan.empty:
            plan = today_plan.iloc[0]
            with st.container(border=True):
                c1, c2 = st.columns(2)
                c1.write(f"**Lead:** {plan['lead_staff']}")
                c2.write(f"**Support:** {plan['support_staff']}")
                
                st.write(f"**Warm Up:** {plan['warm_up']}")
                st.write(f"**Learning Block:** {plan['learning_block']}")
                st.write(f"**Regulation Break:** {plan['regulation_break']}")
                st.write(f"**Social Play:** {plan['social_play']}")
                st.write(f"**Closing Routine:** {plan['closing_routine']}")
                st.info(f"**Materials Needed:** {plan['materials_needed']}")
                
                # Download Button for Today's Plan
                plan_csv = today_plan.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Today's Plan (CSV)", data=plan_csv, file_name=f"Plan_{date.today()}.csv", mime="text/csv")
        else:
            st.info("No session plan has been created for today yet.")
    
    st.divider()

    # --- SECTION B: ATTENDANCE MANAGEMENT ---
    st.subheader("📋 Attendance Management")
    
    # ECE/Admin Only Form
    if user_role in ['ece', 'admin']:
        with st.expander("📝 Log Today's Attendance (ECE/Admin Only)"):
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

    # Staff Attendance Filter
    col_f1, col_f2 = st.columns(2)
    start_att = col_f1.date_input("Attendance From", date.today() - timedelta(days=7))
    end_att = col_f2.date_input("Attendance To", date.today())
    
    df_att = get_attendance_data()
    if not df_att.empty:
        df_att['date'] = pd.to_datetime(df_att['date']).dt.date
        df_att_filt = df_att[(df_att['date'] >= start_att) & (df_att['date'] <= end_att)]
        st.dataframe(df_att_filt.sort_values('date', ascending=False), use_container_width=True, hide_index=True)
    
    st.divider()

    # --- SECTION C: CLINICAL PROGRESS NOTES ---
    st.subheader("📝 Clinical Progress Notes")
    
    # Filter for Progress Notes
    col_p1, col_p2 = st.columns(2)
    p_search = col_p1.text_input("Search Child Name")
    p_days = col_p2.number_input("Look back (days)", value=7)
    
    df_prog = get_data("progress")
    if not df_prog.empty:
        df_prog['date'] = pd.to_datetime(df_prog['date']).dt.date
        since_date = date.today() - timedelta(days=p_days)
        
        # Apply Filters
        df_p_filt = df_prog[df_prog['date'] >= since_date]
        if p_search:
            df_p_filt = df_p_filt[df_p_filt['child_name'].str.contains(p_search, case=False)]
        
        # Display full notes
        if not df_p_filt.empty:
            for _, row in df_p_filt.sort_values('date', ascending=False).iterrows():
                with st.expander(f"{row['date']} - {row['child_name']} ({row['discipline']}) - Status: {row['status']}"):
                    st.write(f"**Goal Area:** {row['goal_area']}")
                    st.write(f"**Note:** {row['notes']}")
                    st.caption(f"Author: {row.get('author', 'Unknown')}")
        else:
            st.write("No progress notes found for this criteria.")

def show_parent_dashboard(child_link):
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
        df_filtered = df_att[(df_att['date'] >= start_d) & (df_att['date'] <= end_d)]
        
        if not df_filtered.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Present", len(df_filtered[df_filtered['status'] == 'Present']))
            m2.metric("Absent", len(df_filtered[df_filtered['status'] == 'Absent']))
            m3.metric("Late", len(df_filtered[df_filtered['status'] == 'Late']))
            st.dataframe(df_filtered[['date', 'status']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)
