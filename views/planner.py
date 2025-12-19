# views/planner.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from .database import get_data, save_plan, update_plan_extras

def show_page():
    st.title("📅 Daily Planner & Coordination")
    username = st.session_state.get("username", "User")
    role = st.session_state.get("role", "").lower()

    # --- SECTION 1: CREATE NEW PLAN ---
    with st.expander("➕ Create New Daily Plan", expanded=False):
        with st.form("create_plan_form", clear_on_submit=True):
            st.markdown("### Plan Details")
            p_date = st.date_input("Date for Plan", date.today())
            lead = st.text_input("Lead Staff / Teacher", value=username)
            
            col1, col2 = st.columns(2)
            wu = col1.text_area("Warm Up Routine")
            lb = col2.text_area("Learning Block")
            rb = col1.text_area("Regulation Break")
            sp = col2.text_area("Social Play")
            
            cr = st.text_area("Closing Routine")
            mn = st.text_area("Materials Needed")
            notes = st.text_area("Internal Team Notes")
            
            if st.form_submit_button("Publish Plan to Team"):
                if wu and lb:
                    save_plan(p_date, lead, "Team", wu, lb, rb, sp, cr, mn, notes, username)
                    st.success("Plan successfully published!")
                    st.rerun()
                else:
                    st.error("Please fill in the required fields.")

    st.divider()

    # --- SECTION 2: FILTERING & BOARD ---
    st.subheader("📋 Team Planning Board")
    
    # Date Range Filter
    c1, c2 = st.columns(2)
    start_date = c1.date_input("Start Date", date.today() - timedelta(days=1))
    end_date = c2.date_input("End Date", date.today() + timedelta(days=7))

    # FETCH ALL DATA
    df = get_data("session_plans")
    
    if not df.empty:
        df['date_dt'] = pd.to_datetime(df['date']).dt.date
        
        # APPLY FILTER
        mask = (df['date_dt'] >= start_date) & (df['date_dt'] <= end_date)
        filtered_plans = df.loc[mask].sort_values('date_dt', ascending=True)
        
        if filtered_plans.empty:
            st.info("No plans found for this date range.")
        
        for index, row in filtered_plans.iterrows():
            # Use an Expander so the list is "collapsed" by default
            with st.expander(f"🗓️ {row['date']} | Lead: {row['lead_staff']}", expanded=False):
                
                # Visual Layout
                st.caption(f"Created by: {row['author']}")
                p1, p2 = st.columns(2)
                with p1:
                    st.markdown(f"**🧘 Warm Up:**\n{row['warm_up']}")
                    st.markdown(f"**🧠 Learning Block:**\n{row['learning_block']}")
                with p2:
                    st.markdown(f"**🏃 Regulation Break:**\n{row['regulation_break']}")
                    st.markdown(f"**🤝 Social Play:**\n{row['social_play']}")
                
                st.markdown(f"**🎨 Materials:** {row['materials_needed']}")
                if row['internal_notes']:
                    st.caption(f"📝 **Notes:** {row['internal_notes']}")

                # --- COORDINATION COMMENTS ---
                st.markdown("---")
                st.write("💬 **Team Coordination**")
                if row['staff_comments']:
                    st.info(row['staff_comments'])
                
                with st.form(key=f"comment_form_{row['id']}", clear_on_submit=True):
                    new_comment = st.text_input("Add a suggestion:", key=f"in_c_{row['id']}")
                    if st.form_submit_button("Post Comment"):
                        if new_comment:
                            timestamp = pd.Timestamp.now().strftime("%H:%M")
                            formatted = f"\n**{username} ({timestamp}):** {new_comment}"
                            update_plan_extras(row['id'], formatted, None)
                            st.rerun()

                # --- SPECIALIST SUPERVISION (QA) ---
                st.markdown("---")
                st.write("🧐 **Specialist Supervision / Observation Report**")
                
                # Role-based visibility
                specialist_roles = ['admin', 'bc', 'ot', 'slp']
                
                # Display existing supervision if it exists
                if row['supervision_notes']:
                    st.warning(f"**Specialist Feedback:**\n{row['supervision_notes']}")
                else:
                    st.caption("No specialist observation recorded yet.")

                # Input logic for Specialists ONLY
                if role in specialist_roles:
                    # We use a toggle to open the edit box so it doesn't show for everyone simultaneously
                    if st.checkbox("✍️ Add/Edit Observation", key=f"chk_{row['id']}"):
                        # We do NOT use 'value=' here to prevent ghosting across users
                        sup_note = st.text_area("Clinical recommendations:", 
                                               placeholder="Type your recommendations here...",
                                               key=f"sup_area_{row['id']}")
                        
                        if st.button("Save Report", key=f"save_sup_{row['id']}"):
                            if sup_note:
                                # Prepend the specialist name for clarity
                                final_note = f"[{username.upper()} - {date.today()}]: {sup_note}"
                                update_plan_extras(row['id'], None, final_note)
                                st.success("Report saved.")
                                st.rerun()
                            else:
                                st.error("Note cannot be empty.")
    else:
        st.info("No plans available.")
