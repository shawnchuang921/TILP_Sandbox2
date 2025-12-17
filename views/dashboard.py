# views/dashboard.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from .database import get_list_data, get_data, upsert_attendance, get_attendance_data, delete_attendance

def show_page():
    st.title("📊 Program Dashboard")
    
    # Retrieve user session info
    user_role = st.session_state.get('role', '').lower()
    username = st.session_state.get('username')
    child_link = st.session_state.get('child_link')

    # --- 1. PARENT VIEW ---
    if user_role == 'parent':
        show_parent_dashboard(child_link)
        return

    # --- 2. STAFF & ADMIN VIEW ---
    
    # --- SECTION A: SESSION PLAN EXPLORER ---
    st.subheader("📅 Session Plan Explorer")
    df_plans = get_data("session_plans")
    
    if not df_plans.empty:
        col_s1, col_s2 = st.columns(2)
        plan_start = col_s1.date_input("Plans From", date.today() - timedelta(days=7), key="st_plan_start")
        plan_end = col_s2.date_input("Plans To", date.today() + timedelta(days=7), key="st_plan_end")
        
        df_plans['date'] = pd.to_datetime(df_plans['date']).dt.date
        mask = (df_plans['date'] >= plan_start) & (df_plans['date'] <= plan_end)
        filtered_plans = df_plans.loc[mask].sort_values('date', ascending=False)
        
        if not filtered_plans.empty:
            # Download Plans Button
            csv_plans = filtered_plans.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Filtered Plans (CSV)",
                data=csv_plans,
                file_name=f"Plans_{plan_start}_to_{plan_end}.csv",
                mime="text/csv",
                key="dl_staff_plans"
            )

            for _, plan in filtered_plans.iterrows():
                is_today = plan['date'] == date.today()
                label = f"🗓️ {plan['date']} - Lead: {plan['lead_staff']} {'(TODAY)' if is_today else ''}"
                with st.expander(label, expanded=is_today):
                    st.write(f"**Lead:** {plan['lead_staff']} | **Support:** {plan['support_staff']}")
                    st.write(f"**Warm Up:** {plan['warm_up']}")
                    st.write(f"**Learning Block:** {plan['learning_block']}")
                    st.write(f"**Regulation Break:** {plan['regulation_break']}")
                    st.write(f"**Social Play:** {plan['social_play']}")
                    st.write(f"**Closing Routine:** {plan['closing_routine']}")
                    st.info(f"**Materials:** {plan['materials_needed']}")
                    if plan.get('internal_notes'):
                        st.warning(f"**Internal Notes:** {plan['internal_notes']}")
        else:
            st.info("No plans found for this date range.")
    else:
        st.info("No session plans in database.")
    
    st.divider()

    # --- SECTION B: ATTENDANCE MANAGEMENT ---
    st.subheader("📋 Attendance Management")
    if user_role in ['ece', 'admin']:
        with st.expander("📝 Log Today's Attendance (ECE/Admin Only)"):
            with st.form("staff_att_form"):
                att_date = st.date_input("Date", date.today())
                child_df = get_list_data("children")
                if not child_df.empty:
                    selected_child = st.selectbox("Select Child", child_df['child_name'].tolist())
                    status = st.radio("Status", ["Present", "Absent", "Late"], horizontal=True)
                    if st.form_submit_button("Submit Attendance"):
                        upsert_attendance(att_date.isoformat(), selected_child, status, username)
                        st.success(f"Logged {status} for {selected_child}")
                        st.rerun()

    # Staff Attendance Filter/Table
    st.write("### Filter Attendance History")
    col_a1, col_a2 = st.columns(2)
    a_start = col_a1.date_input("Attendance From", date.today() - timedelta(days=7), key="st_att_s")
    a_end = col_a2.date_input("Attendance To", date.today(), key="st_att_e")

    df_att = get_attendance_data()
    if not df_att.empty:
        df_att['date'] = pd.to_datetime(df_att['date']).dt.date
        df_att_f = df_att[(df_att['date'] >= a_start) & (df_att['date'] <= a_end)]
        st.dataframe(df_att_f.sort_values('date', ascending=False), use_container_width=True, hide_index=True)
    
    st.divider()

    # --- SECTION C: CLINICAL PROGRESS NOTES ---
    st.subheader("📝 Clinical Progress Notes")
    col_p1, col_p2 = st.columns(2)
    p_search = col_p1.text_input("Search Child Name", key="st_p_search")
    p_days = col_p2.number_input("Look back (days)", value=30, key="st_p_days")
    
    df_prog = get_data("progress")
    if not df_prog.empty:
        df_prog['date'] = pd.to_datetime(df_prog['date']).dt.date
        since = date.today() - timedelta(days=p_days)
        df_p_filt = df_prog[df_prog['date'] >= since].copy()
        
        if p_search:
            df_p_filt = df_p_filt[df_p_filt['child_name'].str.contains(p_search, case=False)]
        
        if not df_p_filt.empty:
            # Download Progress Button
            csv_prog = df_p_filt.sort_values('date', ascending=False).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Filtered Progress (CSV)", data=csv_prog, file_name="Progress_Report.csv", key="dl_st_prog")
            
            for _, row in df_p_filt.sort_values('date', ascending=False).iterrows():
                with st.expander(f"{row['date']} - {row['child_name']} ({row['discipline']})"):
                    st.write(f"**Goal Area:** {row['goal_area']} | **Status:** {row['status']}")
                    st.write(f"**Note:** {row['notes']}")
                    st.caption(f"Author: {row.get('author', 'Unknown')}")
    else:
        st.info("No progress notes found.")

# --- PARENT DASHBOARD FUNCTION ---
def show_parent_dashboard(child_link):
    st.subheader(f"👋 Welcome! Records for: {child_link}")
    
    if not child_link or child_link in ["None", "All"]:
        st.error("⚠️ Account not linked to a child. Contact Admin.")
        return

    tab_att, tab_prog = st.tabs(["📊 Attendance History", "📝 Progress Updates"])

    with tab_att:
        c1, c2 = st.columns(2)
        start_d = c1.date_input("From", date.today() - timedelta(days=30), key="p_att_s")
        end_d = c2.date_input("To", date.today(), key="p_att_e")

        df_att = get_attendance_data(child_name=child_link)
        if not df_att.empty:
            df_att['date'] = pd.to_datetime(df_att['date']).dt.date
            df_f = df_att[(df_att['date'] >= start_d) & (df_att['date'] <= end_d)]
            if not df_f.empty:
                m1, m2 = st.columns(2)
                m1.metric("Present", len(df_f[df_f['status'] == 'Present']))
                m2.metric("Absent", len(df_f[df_f['status'] == 'Absent']))
                st.dataframe(df_f[['date', 'status']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("No records in this range.")

    with tab_prog:
        df_prog = get_data("progress")
        if not df_prog.empty:
            df_p_filt = df_prog[df_prog['child_name'] == child_link].copy()
            df_p_filt['date'] = pd.to_datetime(df_p_filt['date']).dt.date
            
            if not df_p_filt.empty:
                lookback = st.slider("Days to show:", 7, 90, 30)
                cutoff = date.today() - timedelta(days=lookback)
                df_disp = df_p_filt[df_p_filt['date'] >= cutoff].sort_values('date', ascending=False)

                for _, row in df_disp.iterrows():
                    with st.container(border=True):
                        st.write(f"📅 **Date:** {row['date']} | 🎯 **Area:** {row['goal_area']}")
                        st.write(f"🔍 **Observation:** {row['notes']}")
                        st.caption(f"Logged by: {row['discipline']}")
            else:
                st.info("No progress updates shared yet.")
