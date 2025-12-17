# views/planner.py
import streamlit as st
import pandas as pd
from datetime import datetime
from .database import save_plan, update_plan, delete_plan, get_data

def show_page():
    st.header("📅 Daily Session Plan")
    user = st.session_state.get('username')
    role = st.session_state.get('role', '').lower()

    if 'edit_plan_data' not in st.session_state:
        st.session_state.edit_plan_data = None

    editing = st.session_state.edit_plan_data is not None
    data = st.session_state.edit_plan_data if editing else {}

    with st.form("planner_form", clear_on_submit=not editing):
        st.subheader("✏️ Edit Plan" if editing else "📝 New Plan")
        c1, c2 = st.columns(2)
        p_date = c1.date_input("Date", datetime.strptime(data['date'], '%Y-%m-%d').date() if editing else datetime.today())
        lead = c2.selectbox("Lead", ["ECE - Lead", "Lead OT", "SLP - Lead", "BC - Lead", "Assistant/BI"], 
                            index=["ECE - Lead", "Lead OT", "SLP - Lead", "BC - Lead", "Assistant/BI"].index(data['lead_staff']) if editing else 0)
        
        supp_list = ["Assistant/BI", "Volunteer", "OT-Assistant", "SLP-Assistant"]
        cur_supp = data.get('support_staff', "").split(", ") if editing else []
        support = st.multiselect("Support Staff", supp_list, default=[s for s in cur_supp if s in supp_list])
        
        mat = st.text_input("Materials", value=data.get('materials_needed', ""))
        wu = st.text_area("Warm Up", value=data.get('warm_up', ""))
        lb = st.text_area("Learning Block", value=data.get('learning_block', ""))
        rb = st.text_area("Regulation Break", value=data.get('regulation_break', ""))
        sp = st.text_area("Social Play", value=data.get('social_play', ""))
        cr = st.text_area("Closing", value=data.get('closing_routine', ""))
        notes = st.text_area("Internal Notes", value=data.get('internal_notes', ""))

        if st.form_submit_button("Save Session Plan"):
            if editing:
                update_plan(data['id'], p_date.isoformat(), lead, support, wu, lb, rb, sp, cr, mat, notes)
                st.session_state.edit_plan_data = None
            else:
                save_plan(p_date.isoformat(), lead, support, wu, lb, rb, sp, cr, mat, notes, user)
            st.success("Plan Saved!")
            st.rerun()

    if editing and st.button("Cancel Edit"):
        st.session_state.edit_plan_data = None
        st.rerun()

    st.divider()
    st.subheader("🗓️ Recent Plans")
    df = get_data("session_plans")
    if not df.empty:
        df = df.sort_values('date', ascending=False)
        for _, row in df.iterrows():
            with st.expander(f"{row['date']} - Lead: {row['lead_staff']} (Author: {row.get('author', 'Unknown')})"):
                st.write(f"**Learning Block:** {row['learning_block']}")
                # Permission check
                if user == row.get('author') or role == 'admin':
                    col_e, col_d = st.columns(2)
                    if col_e.button("✏️ Edit", key=f"e_{row['id']}"):
                        st.session_state.edit_plan_data = row.to_dict()
                        st.rerun()
                    if col_d.button("🗑️ Delete", key=f"d_{row['id']}"):
                        delete_plan(row['id'])
                        st.rerun()
