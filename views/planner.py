# views/planner.py
import streamlit as st
from datetime import date
from .database import save_plan, get_data 
import pandas as pd

def show_page():
    st.header("📅 Daily Session Plan")
    st.info("Plan the structure of the daily session.")

    with st.form("session_plan_form"):
        st.subheader("General Session Details")
        col1, col2 = st.columns(2)
        
        with col1:
            plan_date = st.date_input("Date of Session", date.today())
            session_lead = st.selectbox("Session Lead (ECE Lead / Therapist)", 
                                        ["ECE - Lead", "Lead OT", "SLP - Lead", "BC - Lead", "Assistant/BI"])
        
        with col2:
            support_staff = st.multiselect("Support Staff (Assistants, etc.)", 
                                           ["Assistant/BI", "Volunteer", "OT-Assistant", "SLP-Assistant", "None"])
            materials_needed = st.text_input("Materials Needed", 
                                             placeholder="e.g., Sensory bins, laminated schedule")

        st.divider()
        st.subheader("Core Session Blocks")

        warm_up = st.text_area("Warm-Up Activity", height=100)
        learning_block = st.text_area("Learning Block (Main Activity)", height=100)

        col3, col4 = st.columns(2)
        with col3:
            regulation_break = st.text_area("Regulation Break", height=100)
        with col4:
            social_play = st.text_area("Small Group / Social Play", height=100)

        closing_routine = st.text_area("Closing Routine", height=50)
        internal_notes = st.text_area("Internal Notes for Staff", height=70)

        submitted = st.form_submit_button("📅 Finalize Daily Plan")
        
        if submitted:
            # FIX: We pass support_staff (the list) directly to save_plan
            save_plan(
                plan_date.isoformat(), 
                session_lead, 
                support_staff, 
                warm_up, 
                learning_block, 
                regulation_break, 
                social_play,
                closing_routine,
                materials_needed,
                internal_notes
            )
            st.success(f"Daily Session Plan for {plan_date.isoformat()} finalized!")

    st.divider()
    st.subheader("🗓️ All Daily Plans")
    
    try:
        df_plans = get_data("session_plans")
        if df_plans.empty:
            st.warning("No session plans saved yet.")
            return

        df_plans['date'] = pd.to_datetime(df_plans['date'])
        
        with st.expander("🔎 Filter Daily Plans by Date Range", expanded=True):
            col_start, col_end = st.columns(2)
            min_date = df_plans['date'].min().date()
            max_date = df_plans['date'].max().date()
            start_date = col_start.date_input("Start Date", min_date)
            end_date = col_end.date_input("End Date", max_date)

        df_filtered = df_plans[
            (df_plans['date'].dt.date >= start_date) & 
            (df_plans['date'].dt.date <= end_date)
        ]

        st.dataframe(df_filtered.sort_values(by="date", ascending=False), use_container_width=True, hide_index=True)
        
        if not df_filtered.empty:
            csv_export = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Session Plans to CSV",
                data=csv_export,
                file_name=f'TILP_Session_Plans_{date.today().isoformat()}.csv',
                mime='text/csv'
            )
        
    except Exception as e:
        st.warning(f"Error loading data: {e}")
