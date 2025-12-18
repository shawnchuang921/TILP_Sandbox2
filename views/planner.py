# views/planner.py
import streamlit as st
import pandas as pd
from datetime import date
from .database import get_data, save_plan, update_plan_extras

def show_page():
    st.title("📅 Daily Planner & Coordination")
    username = st.session_state.get("username", "User")
    role = st.session_state.get("role", "").lower()

    # (Keep creation form exactly as is)
    # ... [Assuming existing creation form code is here] ...

    # --- VIEW & COORDINATION SECTION ---
    st.divider()
    st.subheader("📋 Review & Coordinate")
    
    df = get_data("session_plans")
    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
        today = date.today()
        # Filter for today/future
        active_plans = df[df['date'] >= today].sort_values('date')
        
        for index, row in active_plans.iterrows():
            with st.expander(f"{row['date']} - Lead: {row['lead_staff']}"):
                # Show Plan Details
                st.markdown(f"**Warm Up:** {row['warm_up']}")
                st.markdown(f"**Learning Block:** {row['learning_block']}")
                
                # --- NEW: STAFF COMMENTS ---
                st.markdown("---")
                st.write("💬 **Team Coordination**")
                if row['staff_comments']:
                    st.info(row['staff_comments'])
                
                # Add comment
                c_col, s_col = st.columns(2)
                new_comment = c_col.text_input("Add Comment", key=f"c_{row['id']}")
                if c_col.button("Post Comment", key=f"btn_c_{row['id']}"):
                    timestamp = pd.Timestamp.now().strftime("%H:%M")
                    formatted_comment = f"**{username} ({timestamp}):** {new_comment}"
                    update_plan_extras(row['id'], formatted_comment, None)
                    st.rerun()

                # --- NEW: SUPERVISION (OT/SLP/BC Only) ---
                if role in ['admin', 'bc', 'ot', 'slp']:
                    st.write("🧐 **Supervision & QA**")
                    current_sup = row['supervision_notes'] if row['supervision_notes'] else ""
                    sup_note = st.text_area("Observation/Recommendations", value=current_sup, key=f"s_{row['id']}")
                    if st.button("Save Supervision Note", key=f"btn_s_{row['id']}"):
                        update_plan_extras(row['id'], None, sup_note)
                        st.success("Supervision saved")
                        st.rerun()
                elif row['supervision_notes']:
                    st.warning(f"**Supervision Note:** {row['supervision_notes']}")
