# views/dashboard.py
import streamlit as st
import pandas as pd
from .database import get_data, get_attendance_data, get_messages, update_parent_feedback

def show_page():
    role = st.session_state.get('role', '').lower()
    child_link = st.session_state.get('child_link')
    username = st.session_state.get('username')
    
    st.title("📊 Program Dashboard")

    # --- 1. ANNOUNCEMENTS & TO-DO LISTS ---
    # Parents see messages directed to them; Staff/Admin see all active messages
    if role == 'parent':
        target_filter = child_link
    else:
        target_filter = "All"

    msgs = get_messages(target_filter)
    if not msgs.empty:
        st.subheader("📢 Communication Hub")
        for _, msg in msgs.iterrows():
            icon = "✅" if msg['type'] == 'To-Do List' else "🔔"
            with st.container(border=True):
                st.markdown(f"**{icon} {msg['type']}** ({msg['date']})")
                st.write(msg['content'])
                st.caption(f"From: {msg['author']}")
        st.divider()

    # --- 2. ATTENDANCE SNAPSHOT ---
    st.subheader("📅 Attendance Overview")
    if role == 'parent':
        att_df = get_attendance_data(child_name=child_link)
    else:
        att_df = get_attendance_data() # Admin/Staff see all
    
    if not att_df.empty:
        # Show last 5 records
        st.dataframe(att_df.head(5), use_container_width=True, hide_index=True)
    else:
        st.info("No attendance records found.")

    # --- 3. PROGRESS UPDATES & FEEDBACK LOOP ---
    st.subheader("📈 Recent Progress & Therapy Notes")
    
    df = get_data("progress")
    
    # Filter by child if it's a parent
    if role == 'parent' and child_link:
        df = df[df['child_name'] == child_link]
    
    if not df.empty:
        # Sort by ID descending so newest is at the top
        df = df.sort_values('id', ascending=False)
        
        for index, row in df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                
                # Header info
                c1.markdown(f"### {row['discipline']}")
                c1.markdown(f"**Goal Area:** {row['goal_area']}")
                c1.caption(f"Date: {row['date']} | Logged by: {row['author']}")
                
                # Status Badge
                status_colors = {
                    "Mastered": "green",
                    "Progressing": "blue",
                    "Emerging": "orange",
                    "Regression": "red",
                    "Not Observed": "grey"
                }
                s_color = status_colors.get(row['status'], "blue")
                c2.markdown(f"#### :{s_color}[{row['status']}]")

                # Details Area
                with st.expander("🔍 View Details & Interaction"):
                    # Display note for parents
                    if row.get('parent_note'):
                        st.info(f"**Note to Parents:**\n{row['parent_note']}")
                    
                    # Display clinical notes (Hidden from parents)
                    if role != 'parent':
                        st.divider()
                        st.markdown("**🔒 Internal Clinical Notes:**")
                        st.write(row['notes'])
                        if row['media_path']:
                            st.markdown(f"[🔗 View Attached Media]({row['media_path']})")

                    # --- FEEDBACK SECTION ---
                    st.divider()
                    current_fb = row.get('parent_feedback', '')
                    
                    if role == 'parent':
                        st.write("💬 **Your Feedback / Questions**")
                        if current_fb:
                            st.info(f"**Your last comment:** {current_fb}")
                        
                        # The "Disappearing" Form logic
                        with st.form(key=f"fb_form_{row['id']}", clear_on_submit=True):
                            fb_text = st.text_area("Update feedback or ask a question:", placeholder="Staff will see this note...")
                            if st.form_submit_button("Send to Team"):
                                if fb_text:
                                    update_parent_feedback(row['id'], fb_text)
                                    st.success("Feedback sent! Refreshing...")
                                    st.rerun()
                    else:
                        # Staff View of Feedback
                        if current_fb:
                            st.warning(f"💭 **Parent Feedback:** {current_fb}")
                        else:
                            st.caption("No parent feedback yet.")

    else:
        st.info("No progress logs available yet.")
