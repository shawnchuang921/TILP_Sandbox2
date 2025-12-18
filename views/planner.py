# views/planner.py
import streamlit as st
import pandas as pd
from datetime import date
from .database import get_data, save_plan, update_plan_extras

def show_page():
    st.title("📅 Daily Planner & Coordination")
    username = st.session_state.get("username", "User")
    role = st.session_state.get("role", "").lower()

    # --- SECTION 1: CREATE NEW PLAN ---
    # This section allows any staff (Lead or Specialist) to propose a plan.
    with st.expander("➕ Create New Daily Plan", expanded=False):
        with st.form("create_plan_form", clear_on_submit=True):
            st.markdown("### Plan Details")
            p_date = st.date_input("Date for Plan", date.today())
            lead = st.text_input("Lead Staff / Teacher", value=username)
            
            col1, col2 = st.columns(2)
            wu = col1.text_area("Warm Up Routine", placeholder="Morning circle, sensory play...")
            lb = col2.text_area("Learning Block", placeholder="Main activity or lesson...")
            rb = col1.text_area("Regulation Break", placeholder="Movement, quiet time, or snack...")
            sp = col2.text_area("Social Play", placeholder="Group games or peer interaction...")
            
            cr = st.text_area("Closing Routine", placeholder="Pack up, review, or transition...")
            mn = st.text_area("Materials Needed", placeholder="Glue, sensory bins, flashcards...")
            notes = st.text_area("Internal Team Notes", placeholder="Specific reminders for the team...")
            
            if st.form_submit_button("Publish Plan to Team"):
                if wu and lb: # Simple validation
                    save_plan(p_date, lead, "Team", wu, lb, rb, sp, cr, mn, notes, username)
                    st.success("Plan successfully published! It is now visible to all staff below.")
                    st.rerun()
                else:
                    st.error("Please fill in at least the Warm Up and Learning Block.")

    st.divider()

    # --- SECTION 2: TEAM PLANNING BOARD (VISIBILITY FIX) ---
    st.subheader("📋 Team Planning Board")
    st.info("Showing all plans for today and upcoming dates. Specialists can leave recommendations below each plan.")
    
    # FETCH ALL DATA FROM DATABASE
    df = get_data("session_plans")
    
    if not df.empty:
        # Convert the date column to actual date objects for accurate filtering
        df['date_dt'] = pd.to_datetime(df['date']).dt.date
        today = date.today()
        
        # FILTER: Show all plans from today onwards so everyone (ECE, OT, SLP) sees everything
        active_plans = df[df['date_dt'] >= today].sort_values('date_dt')
        
        if active_plans.empty:
            st.warning("No plans have been created for today or the future yet.")
        
        for index, row in active_plans.iterrows():
            # Plan Card
            with st.container(border=True):
                header_col, status_col = st.columns([3, 1])
                header_col.markdown(f"## 🗓️ Plan: {row['date']}")
                header_col.markdown(f"**Lead Staff:** {row['lead_staff']} | **Created by:** {row['author']}")
                
                # Visual Layout of the Plan
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**🧘 Warm Up:**\n{row['warm_up']}")
                    st.markdown(f"**🧠 Learning Block:**\n{row['learning_block']}")
                    st.markdown(f"**🎨 Materials:**\n{row['materials_needed']}")
                with c2:
                    st.markdown(f"**🏃 Regulation Break:**\n{row['regulation_break']}")
                    st.markdown(f"**🤝 Social Play:**\n{row['social_play']}")
                    st.markdown(f"**🔔 Closing:**\n{row['closing_routine']}")
                
                if row['internal_notes']:
                    st.caption(f"📝 **Internal Notes:** {row['internal_notes']}")

                # --- COORDINATION & COMMENTS (Disappearing text fix) ---
                st.markdown("---")
                st.write("💬 **Team Coordination & Feedback**")
                
                if row['staff_comments']:
                    st.info(row['staff_comments'])
                
                # Form to add a comment (clears after submission)
                with st.form(key=f"comment_form_{row['id']}", clear_on_submit=True):
                    new_comment = st.text_input("Add a suggestion or note to this plan:", placeholder="e.g., OT recommendation: use slanted board for this activity.")
                    if st.form_submit_button("Post Comment"):
                        if new_comment:
                            timestamp = pd.Timestamp.now().strftime("%H:%M")
                            # Formats the comment to append to the existing string
                            formatted_comment = f"\n**{username} ({timestamp}):** {new_comment}"
                            update_plan_extras(row['id'], formatted_comment, None)
                            st.rerun()

                # --- SUPERVISION & QA SECTION (Role Restricted) ---
                # Only specialists or admins can write here, but ECE/Assistant can read.
                specialist_roles = ['admin', 'bc', 'ot', 'slp']
                
                st.markdown("---")
                if role in specialist_roles:
                    st.write("🧐 **Specialist Supervision / Observation Report**")
                    current_sup = row['supervision_notes'] if row['supervision_notes'] else ""
                    
                    # Using a key for the text area to ensure state is managed
                    sup_note = st.text_area("Clinical observations or quality recommendations:", 
                                            value=current_sup, 
                                            key=f"sup_input_{row['id']}",
                                            help="Document your feedback for the staff lead here.")
                    
                    if st.button("Save Observation Report", key=f"btn_sup_{row['id']}"):
                        update_plan_extras(row['id'], None, sup_note)
                        st.success("Supervision report saved and shared with the lead.")
                        st.rerun()
                else:
                    # Lead/Assistant View: They only see it if a note exists
                    if row['supervision_notes']:
                        st.warning(f"💡 **Specialist Recommendation:**\n{row['supervision_notes']}")
                    else:
                        st.caption("No specialist observation notes for this plan yet.")
    else:
        st.info("The planning board is currently empty. Use the form above to create the first plan.")
