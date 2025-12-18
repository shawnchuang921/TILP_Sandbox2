# app.py
import streamlit as st
from views.database import init_db, get_user
from views import (
    tracker, 
    planner, 
    dashboard, 
    admin_tools, 
    billing, 
    schedule, 
    library, 
    communication
)

# Initialize Database
init_db()

st.set_page_config(page_title="TILP Connect", layout="wide", page_icon="🧩")

def login_screen():
    st.title("🔐 TILP Connect Login")
    col1, _ = st.columns([1, 2])
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Log In"):
            user_data = get_user(username, password)
            if user_data:
                st.session_state["logged_in"] = True
                st.session_state["role"] = str(user_data["role"]).lower()
                st.session_state["username"] = user_data["username"]
                st.session_state["child_link"] = user_data.get("child_link", "")
                st.rerun()
            else:
                st.error("Incorrect username or password")

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_screen()
        return

    user_role = st.session_state.get("role", "")
    username = st.session_state.get("username", "User")
    
    st.sidebar.title(f"👤 {username.capitalize()}")
    pages = {}

    # Define Pages by Role
    if user_role == "admin":
        pages["🔑 Admin Tools"] = admin_tools.show_page
        pages["📢 Communication Hub"] = communication.show_page
        pages["🗓️ Master Schedule"] = schedule.show_page
        pages["💳 Billing Management"] = billing.show_page
        pages["📂 Resource Library"] = library.show_page
        pages["📊 Program Dashboard"] = dashboard.show_page
    
    elif user_role in ["ot", "slp", "bc", "ece", "assistant", "staff", "therapist"]:
        pages["📊 Program Dashboard"] = dashboard.show_page
        pages["📝 Progress Tracker"] = tracker.show_page
        pages["📅 Daily Planner"] = planner.show_page
        pages["📢 Communication"] = communication.show_page
        pages["📂 Resource Library"] = library.show_page

    elif user_role == "parent":
        pages["📊 My Child's Dashboard"] = dashboard.show_page
        pages["🗓️ Appointments"] = schedule.show_page
        pages["📂 File Library"] = library.show_page
        pages["💳 Billing & Invoices"] = billing.show_page

    selection = st.sidebar.radio("Go to:", list(pages.keys()))
    
    if st.sidebar.button("Log Out"):
        st.session_state.clear()
        st.rerun()

    # Execute the selected page function
    pages[selection]()

if __name__ == "__main__":
    main()
