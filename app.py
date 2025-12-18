import streamlit as st
# Import Database functions
from views.database import init_db, get_user
# Import ALL View Modules (including the new ones)
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

# Initialize Database on app launch
init_db()

# Page Configuration
st.set_page_config(page_title="TILP Connect", layout="wide", page_icon="🧩")

# --- LOGIN SCREEN ---
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

# --- MAIN APP LOGIC ---
def main():
    # Ensure session state exists
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # Show Login if not authenticated
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
        pages["📢 Communication Hub"] = communication.show_page
        pages["🗓️ Master Schedule"] = schedule.show_page
        pages["💳 Billing Management"] = billing.show_page
        pages["📂 Resource Library"] = library.show_page
    
    # 2. STAFF TOOLS (Therapists, ECE, Staff)
    # Includes Admin so they can see staff views too
    staff_roles = ["admin", "ot", "slp", "bc", "ece", "assistant", "staff", "therapist"]
    
    if user_role in staff_roles:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Clinical Tools**")
        pages["📝 Progress Tracker"] = tracker.show_page
        pages["📅 Daily Planner"] = planner.show_page
        pages["📂 Resource Library"] = library.show_page
        
        # Staff (non-admin) can send messages too
        if user_role != "admin": 
             pages["📢 Communication"] = communication.show_page

        # Admin sees dashboard in a different spot, but staff see it here
        if user_role != "admin":
            pages["📊 Program Dashboard"] = dashboard.show_page
        else:
             # Add a special entry for Admin to see the dashboard
             pages["📊 Program Dashboard"] = dashboard.show_page

    # 3. PARENT TOOLS
    if user_role == "parent":
        pages[f"📊 Dashboard"] = dashboard.show_page
        pages[f"🗓️ Appointments"] = schedule.show_page
        pages[f"📂 File Library"] = library.show_page
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
