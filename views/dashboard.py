# views/dashboard.py
import streamlit as st
import pandas as pd
from .database import get_data, get_attendance_data, get_messages, update_parent_feedback

def show_page():
    role = st.session_state.get('role', '').lower()
    child_link = st.session_state.get('child_link')
    
    st.title("📊 Dashboard")

    # --- 1. MESSAGE BOARD (New) ---
    if role == 'parent' and child_link:
        msgs = get_messages(child_link)
        if not msgs.empty:
            st.info("📢 **New Messages**")
            for _, msg in msgs.iterrows():
                icon = "✅" if msg['type'] == 'To-Do List' else "🔔"
                with st.expander(f"{icon} {msg['type']} - {msg['date']}"):
                    st.write(msg['content'])
                    st.caption(f"Sent by: {msg['author']}")
            st.divider()

    # --- 2. PROGRESS VIEW (Modified) ---
    # (Filter logic remains same)
    df = get_data("progress")
    if role == 'parent' and child_link:
        df = df[df['child_name'] == child_link]
    
    if not df.empty:
        st.subheader("Daily Progress Updates")
        for index, row in df.iterrows():
            # Card Style
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{row['discipline']}** - *{row['goal_area']}*")
                c1.caption(f"Date: {row['date']} | Staff: {row['author']}")
                
                # Show Status Color
                color = "green" if row['status'] == "Mastered" else "orange" if row['status'] == "Progressing" else "grey"
                c2.markdown(f":{color}[**{row['status']}**]")

                # EXPANDER FOR DETAILS
                with st.expander("View Details & Feedback"):
                    # Show Parent Note if exists
                    if row.get('parent_note'):
                        st.success(f"**Note for Parents:**\n{row['parent_note']}")
                    
                    # Show Clinical Note (If Staff/Admin)
                    if role != 'parent':
                        st.markdown(f"**Clinical Note:** {row['notes']}")

                    # --- PARENT FEEDBACK SECTION ---
                    current_fb = row.get('parent_feedback', '')
                    if role == 'parent':
                        fb_input = st.text_area("Your Feedback/Question:", value=current_fb if current_fb else "", key=f"fb_{row['id']}")
                        if st.button("Send Feedback", key=f"btn_{row['id']}"):
                            update_parent_feedback(row['id'], fb_input)
                            st.success("Feedback sent to staff!")
                    elif current_fb:
                        st.info(f"**Parent Feedback:** {current_fb}")
