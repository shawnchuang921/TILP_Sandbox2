# app.py
import streamlit as st
# FIXED: Database functions are now imported from the new location (views.database)
from views.database import init_db, get_user
# Import the new admin tools page
from views import tracker, planner, dashboard, admin_tools 

# Initialize Database
init_db()

# Page Configuration
st.set_page_config(page_title="TILP Connect", layout="wide", page_icon="🧩")

# --- DATABASE AUTHENTICATION ---
def login_screen():
    st.title("🔐 TILP Connect Login")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Log In"):
            user_data = get_user(username, password)
            
            if user_data:
                st.session_state["logged_in"] = True
                # FIX 1: Change "user_role" key to "role" for consistency with tracker.py
                st.session_state["role"] = user_data["role"] 
                st.session_state["username"] = user_data["username"]
                # Store the child link for parent filtering
                st.session_state["child_link"] = user_data["child_link"]
                st.success(f"Welcome, {user_data['username']} ({user_data['role']})!")
                st.rerun()
            else:
                st.error("Incorrect username or password")

def main():
    # Check Login Status
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_screen()
        return

    # --- SIDEBAR NAVIGATION ---
    # FIX 2: Retrieve role using the corrected key "role"
    user_role = st.session_state["role"] 
    username = st.session_state["username"]
    st.sidebar.title(f"👤 User: {username.capitalize()}")
    st.sidebar.markdown(f"**Role:** {user_role.upper()}")
    
    # Define available pages based on Role
    pages = {}
    
    # Admin has all permissions
    if user_role == "admin":
        pages["🔑 Admin Tools"] = admin_tools.show_page
    
    # Staff/Therapists/Admin roles
    if user_role in ["admin", "OT", "SLP", "BC", "ECE", "Assistant", "staff"]:
        pages["📝 Progress Tracker"] = tracker.show_page
        pages["📅 Daily Planner"] = planner.show_page
    
    # Dashboard view changes based on role
    if user_role == "parent":
        child_name = st.session_state.get("child_link", "My Child")
        pages[f"📊 My Child's Dashboard"] = dashboard.show_page
    else:
        pages["📊 Dashboard & Reports"] = dashboard.show_page

    selection = st.sidebar.radio("Go to:", list(pages.keys()))
    
    if st.sidebar.button("Log Out"):
        st.session_state.clear()
        st.session_state["logged_in"] = False
        st.rerun()

    # Display Selected Page
    pages[selection]()

if __name__ == "__main__":
    main()
