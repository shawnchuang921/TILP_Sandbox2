# views/communication.py
import streamlit as st
from .database import create_message, get_list_data

def show_page():
    st.title("📢 Communication Hub")
    
    role = st.session_state.get('role', '').lower()
    username = st.session_state.get('username')
    
    if role == 'parent':
        st.error("Access Restricted")
        return

    st.markdown("Use this page to send **Announcements** or **To-Do Lists** to parents.")

    with st.form("comm_form"):
        msg_type = st.selectbox("Message Type", ["Announcement", "To-Do List"])
        
        child_df = get_list_data("children")
        targets = ["All"] + (child_df['child_name'].tolist() if not child_df.empty else [])
        target = st.selectbox("Recipient", targets, help="'All' sends to every parent.")
        
        content = st.text_area("Message / Tasks", height=150, placeholder="- Bring rain boots\n- Sign consent form\n- Review home plan")
        
        if st.form_submit_button("Send Message"):
            create_message(msg_type, target, content, username)
            st.success("Message Sent!")
