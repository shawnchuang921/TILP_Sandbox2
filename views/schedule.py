# views/schedule.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from .database import get_appointments, create_appointment, get_list_data

def show_page():
    st.title("🗓️ Schedule & Appointments")
    
    role = st.session_state.get('role', '').lower()
    child_link = st.session_state.get('child_link')

    # --- ADMIN VIEW: Schedule Appointment ---
    if role == 'admin':
        with st.expander("➕ Schedule New Appointment"):
            with st.form("appt_form"):
                d_col, t_col = st.columns(2)
                a_date = d_col.date_input("Date", date.today())
                a_time = t_col.time_input("Time", datetime.now().time())
                
                child_df = get_list_data("children")
                children = child_df['child_name'].tolist() if not child_df.empty else []
                s_child = st.selectbox("Child", children)
                
                d_type = st.selectbox("Type", ["OT Session", "SLP Session", "BC Consultation", "Assessment", "Other"])
                staff = st.text_input("Provider Name")
                cost = st.number_input("Session Cost ($)", value=0.0)
                
                if st.form_submit_button("Book Appointment"):
                    create_appointment(a_date, str(a_time), s_child, d_type, staff, cost, "Scheduled")
                    st.success("Appointment booked.")
                    st.rerun()
        st.divider()

    # --- PARENT VIEW ---
    df = pd.DataFrame()

    if role == 'parent':
        if child_link and child_link not in ["None", "All"]:
            df = get_appointments(child_name=child_link)
            st.subheader(f"Upcoming Schedule for {child_link}")
        else:
            st.error("No child linked.")
    elif role == 'admin':
        # Admin sees all
        df = get_appointments()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Separate Past vs Upcoming
        today = date.today()
        upcoming = df[df['date'] >= today].sort_values('date')
        past = df[df['date'] < today].sort_values('date', ascending=False)
        
        tab1, tab2 = st.tabs(["📅 Upcoming", "📜 Past History"])
        
        with tab1:
            if not upcoming.empty:
                for _, row in upcoming.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f"**{row['date']} @ {row['time']}** — *{row['discipline']}*")
                        c1.caption(f"Provider: {row['staff']}")
                        c2.write(f"**${row['cost']}**")
            else:
                st.info("No upcoming appointments.")

        with tab2:
            st.dataframe(past[['date', 'time', 'discipline', 'staff', 'cost']], use_container_width=True, hide_index=True)
            
    else:
        st.info("No appointments found.")
