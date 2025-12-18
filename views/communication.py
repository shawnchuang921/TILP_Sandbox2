# views/communication.py
import streamlit as st
from .database import create_message, get_list_data

def show_page():
    st.title("📢 Communication Hub")
    username = st.session_state.get('username')

    with st.form("comm_form", clear_on_submit=True):
        msg_type = st.selectbox("Message Type", ["Announcement", "To-Do List"])
        
        child_df = get_list_data("children")
        targets = ["All"] + (child_df['child_name'].tolist() if not child_df.empty else [])
        target = st.selectbox("Recipient", targets)
        
        content = st.text_area("Message / Tasks")
        
        if st.form_submit_button("Send to Parent Portal"):
            create_message(msg_type, target, content, username)
            st.success("Sent! Form cleared.")
