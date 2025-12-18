# views/communication.py
import streamlit as st
from .database import create_message, get_list_data

def show_page():
    st.title("📢 Communication Hub")
    st.markdown("Use this portal to send announcements or To-Do lists directly to parent dashboards.")
    
    username = st.session_state.get('username')
    
    # Form to send messages
    with st.form("send_message_form", clear_on_submit=True):
        st.subheader("Create New Message")
        
        msg_type = st.selectbox("Type of Message", ["Announcement", "To-Do List"])
        
        # Load children for targeting
        child_df = get_list_data("children")
        child_names = child_df['child_name'].tolist() if not child_df.empty else []
        target = st.selectbox("Recipient", ["All"] + child_names)
        
        content = st.text_area("Message Content", placeholder="Enter the details of your announcement or list items here...")
        
        submit = st.form_submit_button("Send Message")
        
        if submit:
            if content:
                create_message(msg_type, target, content, username)
                st.success(f"Successfully sent {msg_type} to {target}!")
            else:
                st.error("Message content cannot be empty.")

    st.divider()
    st.subheader("Message Guidelines")
    st.info("""
    - **Announcements:** General updates (e.g., School closures, event reminders).
    - **To-Do Lists:** Specific tasks for parents (e.g., 'Bring extra clothes', 'Sign IEP form').
    - **Visibility:** Parents will see these at the very top of their dashboard.
    """)
