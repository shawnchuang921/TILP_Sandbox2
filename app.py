# app.py (Final Version with Billing & Schedule)
import streamlit as st
from views.database import init_db, get_user
# IMPORT NEW MODULES HERE
from views import tracker, planner, dashboard, admin_tools, billing, schedule

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
                st.session_state["role"] = str(user_data["role"])
                st.session_state["username"] = user_data["username"]
                st.session_state["child_link"] = user_data.get("child_link", "")
                st.success(f"Welcome, {user_data['username']}!")
                st.rerun()
            else:
                st.error("Incorrect username or password")

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_screen()
        return

    # --- SIDEBAR NAVIGATION ---
    user_role = str(st.session_state.get("role", "")).lower()
    username = st.session_state.get("username", "User")
    
    st.sidebar.title(f"👤 {username.capitalize()}")
    st.sidebar.markdown(f"**Role:** {user_role.upper()}")
    
    # Define available pages based on Role
    pages = {}
    
    # 1. ADMIN TOOLS
    if user_role == "admin":
        pages["🔑 Admin Tools"] = admin_tools.show_page
        pages["🗓️ Master Schedule"] = schedule.show_page
        pages["💳 Billing Management"] = billing.show_page
    
    # 2. STAFF TOOLS (Therapists, ECE, Staff)
    # Note: Staff view remains exactly as it was.
    staff_roles = ["admin", "ot", "slp", "bc", "ece", "assistant", "staff", "therapist"]
    if user_role in staff_roles:
        pages["📝 Progress Tracker"] = tracker.show_page
        pages["📅 Daily Planner"] = planner.show_page
        # If user is Admin, they see the dashboard here too
        if user_role == "admin":
            pages["📊 Program Dashboard"] = dashboard.show_page
        else:
            pages["📊 Dashboard & Reports"] = dashboard.show_page
    
    # 3. PARENT TOOLS (Expanded)
    if user_role == "parent":
        # 1. Existing Dashboard (Progress & Attendance) - UNTOUCHED
        pages[f"📊 Dashboard"] = dashboard.show_page
        
        # 2. NEW: Appointment Schedule
        pages[f"🗓️ Appointments"] = schedule.show_page
        
        # 3. NEW: Billing & Invoices
        pages[f"💳 Billing & Invoices"] = billing.show_page

    # Sidebar Selection
    selection = st.sidebar.radio("Go to:", list(pages.keys()))
    
    st.sidebar.divider()
    if st.sidebar.button("Log Out"):
        st.session_state.clear()
        st.rerun()

    # Display Selected Page
    try:
        pages[selection]()
    except Exception as e:
        st.error(f"Error loading page: {e}")

if __name__ == "__main__":
    main()
