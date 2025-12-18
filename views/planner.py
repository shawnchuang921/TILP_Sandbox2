# views/planner.py
import streamlit as st
import pandas as pd
from datetime import date
from .database import get_data, save_plan, update_plan_extras

def show_page():
    st.title("📅 Daily Planner & Coordination")
    username = st.session_state.get("username", "User")
    role = st.session_state.get("role", "").lower()

    # SECTION 1: CREATE PLAN
    with st.expander("➕ Create New Daily Plan"):
        with st.form("create_plan_form", clear_on_submit=True):
            p_date = st.date_input("Date for Plan", date.today())
            lead = st.text_input("Lead Staff", value=username)
            wu = st.text_area("Warm Up")
            lb = st.text_area("Learning Block")
            rb = st.text_area("Regulation Break")
            sp = st.text_area("Social Play")
            cr = st.text_area("Closing Routine")
            mn = st.text_area("Materials Needed")
            notes = st.text_area("Internal Notes")
            
            if st.form_submit_button("Submit Plan"):
                save_plan(p_date, lead, "Team", wu, lb, rb, sp, cr, mn, notes, username)
                st.success("Plan Published!")
                st.rerun()

    st.divider()
    st.subheader("📋 Team Planning Board")
    
    # FETCH ALL DATA
    df = get_data("session_plans")
    if not df.empty:
        # Convert date column to actual date objects for comparison
        df['date_dt'] = pd.to_datetime(df['date']).dt.date
        today = date.today()
        
        # Filter for ALL plans from today onwards
        active_plans = df[df['date_dt'] >= today].sort_values('date_dt')
        
        if active_plans.empty:
            st.info("No active plans found for today or upcoming dates.")
        
        for index, row in active_plans.iterrows():
            with st.container(border=True):
                st.markdown(f"### 🗓️ Plan for: {row['date']}")
                st.caption(f"Lead: {row['lead_staff']} | Created by: {row['author']}")
                
                col1, col2 = st.columns(2)
                col1.markdown(f"**Warm Up:** {row['warm_up']}")
                col1.markdown(f"**Learning Block:** {row['learning_block']}")
                col2.markdown(f"**Social Play:** {row['social_play']}")
                col2.markdown(f"**Closing:** {row['closing_routine']}")

                # TEAM COMMENTS
                st.markdown("---")
                if row['staff_comments']:
                    st.info(f"💬 **Team Discussion:**\n{row['staff_comments']}")
                
                with st.form(f"comment_form_{row['id']}", clear_on_submit=True):
                    new_comment = st.text_input("Add a comment/suggestion to this plan:")
                    if st.form_submit_button("Post to Team"):
                        timestamp = pd.Timestamp.now().strftime("%H:%M")
                        formatted = f"\n**{username} ({timestamp}):** {new_comment}"
                        update_plan_extras(row['id'], formatted, None)
                        st.rerun()

                # SUPERVISION (QA)
                if role in ['admin', 'bc', 'ot', 'slp']:
                    with st.expander("🧐 Supervision / Observation Report (QA)"):
                        current_sup = row['supervision_notes'] if row['supervision_notes'] else ""
                        sup_note = st.text_area("Recommendations for Lead/Assistant", value=current_sup, key=f"sup_{row['id']}")
                        if st.button("Save QA Report", key=f"btn_sup_{row['id']}"):
                            update_plan_extras(row['id'], None, sup_note)
                            st.success("Supervision documented.")
                            st.rerun()
                elif row['supervision_notes']:
                    st.warning(f"💡 **Specialist Recommendation:** {row['supervision_notes']}")
