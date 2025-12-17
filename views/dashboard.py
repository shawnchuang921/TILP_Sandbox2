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
    
    # --- SECTION A: SESSION PLAN ARCHIVE ---
    st.subheader("📅 Session Plan Explorer")
    df_plans = get_data("session_plans")
    
    if not df_plans.empty:
        col_s1, col_s2 = st.columns(2)
        plan_start = col_s1.date_input("Plans From", date.today() - timedelta(days=7), key="ps_start")
        plan_end = col_s2.date_input("Plans To", date.today() + timedelta(days=7), key="ps_end")
        
        df_plans['date'] = pd.to_datetime(df_plans['date']).dt.date
        mask = (df_plans['date'] >= plan_start) & (df_plans['date'] <= plan_end)
        filtered_plans = df_plans.loc[mask].sort_values('date', ascending=False)
        
        if not filtered_plans.empty:
            csv_range = filtered_plans.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Filtered Plans (CSV)",
                data=csv_range,
                file_name=f"Plans_{plan_start}_to_{plan_end}.csv",
                mime="text/csv",
                key="dl_plans_final"
            )

            for _, plan in filtered_plans.iterrows():
                is_today = plan['date'] == date.today()
                label = f"🗓️ {plan['date']} - Lead: {plan['lead_staff']} {'(TODAY)' if is_today else ''}"
                with st.expander(label, expanded=is_today):
                    st.write(f"**Lead:** {plan['lead_staff']} | **Support:** {plan['support_staff']}")
                    st.write(f"**Learning Block:** {plan['learning_block']}")
                    st.info(f"**Materials:** {plan['materials_needed']}")
    
    st.divider()

    # --- SECTION B: ATTENDANCE MANAGEMENT ---
    st.subheader("📋 Attendance Management")
    if user_role in ['ece', 'admin']:
        with st.expander("📝 Log Today's Attendance"):
            with st.form("att_form"):
                att_date = st.date_input("Date", date.today())
                child_df = get_list_data("children")
                if not child_df.empty:
                    selected_child = st.selectbox("Select Child", child_df['child_name'].tolist())
                    status = st.radio("Status", ["Present", "Absent", "Late"], horizontal=True)
                    if st.form_submit_button("Submit Attendance"):
                        upsert_attendance(att_date.isoformat(), selected_child, status, username)
                        st.rerun()

    df_att = get_attendance_data()
    if not df_att.empty:
        df_att['date'] = pd.to_datetime(df_att['date']).dt.date
        st.dataframe(df_att.sort_values('date', ascending=False).head(20), use_container_width=True, hide_index=True)
    
    st.divider()

    # --- SECTION C: CLINICAL PROGRESS NOTES (FIXED DOWNLOAD) ---
    st.subheader("📝 Clinical Progress Notes")
    
    col_p1, col_p2 = st.columns(2)
    p_search = col_p1.text_input("Search Child Name", key="prog_search_input")
    p_days = col_p2.number_input("Look back (days)", value=30, key="prog_lookback_input")
    
    df_prog = get_data("progress")
    if not df_prog.empty:
        # 1. Clean and Filter Data
        df_prog['date'] = pd.to_datetime(df_prog['date']).dt.date
        since_date = date.today() - timedelta(days=p_days)
        df_p_filt = df_prog[df_prog['date'] >= since_date].copy()
        
        if p_search:
            df_p_filt = df_p_filt[df_p_filt['child_name'].str.contains(p_search, case=False)]
        
        # 2. Render Download Button if data exists
        if not df_p_filt.empty:
            # Sort for clean export
            df_export = df_p_filt.sort_values('date', ascending=False)
            csv_prog_data = df_export.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Download Filtered Progress Notes (CSV)",
                data=csv_prog_data,
                file_name=f"Progress_Report_{date.today()}.csv",
                mime="text/csv",
                key="btn_download_progress_final_v2" # Unique key to avoid collisions
            )
            
            # 3. Display individual notes in Expanders
            for _, row in df_export.iterrows():
                with st.expander(f"{row['date']} - {row['child_name']} ({row['discipline']})"):
                    st.write(f"**Goal Area:** {row['goal_area']} | **Status:** {row['status']}")
                    st.write(f"**Note:** {row['notes']}")
                    st.caption(f"Author: {row.get('author', 'Unknown')}")
        else:
            st.info("No progress notes match your search/filters.")
    else:
        st.info("No progress notes found in the database.")

def show_parent_dashboard(child_link):
    st.subheader(f"👋 Attendance Overview for {child_link}")
    df_att = get_attendance_data(child_name=child_link)
    if not df_att.empty:
        df_att['date'] = pd.to_datetime(df_att['date']).dt.date
        st.dataframe(df_att.sort_values('date', ascending=False), use_container_width=True, hide_index=True)
