# views/admin_tools.py
import streamlit as st
import pandas as pd
from sqlalchemy import text
from .database import (
    ENGINE, get_list_data, upsert_user, delete_user, 
    upsert_child, delete_child, upsert_list_item, delete_list_item
)

def show_page():
    st.title("🔑 Admin Control Panel")
    st.info("Manage users, children, and system-wide dropdown lists.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "👤 User Management", 
        "👶 Child Profiles", 
        "📂 List Management", 
        "🛠️ Database Repair"
    ])

    # --- TAB 1: USER MANAGEMENT ---
    with tab1:
        st.subheader("Add / Update System Users")
        
        # Get existing children for the 'child_link' dropdown
        child_df = get_list_data("children")
        child_options = ["None", "All"] + (child_df['child_name'].tolist() if not child_df.empty else [])

        with st.form("user_form"):
            col1, col2 = st.columns(2)
            u_name = col1.text_input("Username")
            u_pass = col2.text_input("Password (leave blank to keep existing during update)", type="password")
            
            u_role = col1.selectbox("Role", ["admin", "ECE", "OT", "SLP", "BC", "Assistant", "parent"])
            u_link = col2.selectbox("Link to Child (for Parents)", child_options)
            
            if st.form_submit_button("Save User"):
                upsert_user(u_name, u_pass, u_role, u_link)
                st.success(f"User '{u_name}' processed.")
                st.rerun()

        st.divider()
        st.subheader("Existing Users")
        users = get_list_data("users")
        if not users.empty:
            st.dataframe(users, use_container_width=True, hide_index=True)
            
            del_user = st.selectbox("Select User to Delete", [""] + users['username'].tolist())
            if st.button("🗑️ Delete Selected User", type="secondary"):
                if del_user:
                    delete_user(del_user)
                    st.warning(f"User {del_user} deleted.")
                    st.rerun()

    # --- TAB 2: CHILD PROFILES ---
    with tab2:
        st.subheader("Register Child Profiles")
        with st.form("child_form"):
            c_name = st.text_input("Child's Full Name")
            p_user = st.text_input("Parent Username (must match a user above)")
            dob = st.date_input("Date of Birth")
            
            if st.form_submit_button("Save Child Profile"):
                upsert_child(c_name, p_user, dob.isoformat())
                st.success(f"Profile for {c_name} saved.")
                st.rerun()

        st.divider()
        children = get_list_data("children")
        if not children.empty:
            st.dataframe(children, use_container_width=True, hide_index=True)
            del_c = st.selectbox("Select Child to Delete", [""] + children['child_name'].tolist())
            if st.button("🗑️ Delete Selected Child"):
                if del_c:
                    delete_child(del_c)
                    st.rerun()

    # --- TAB 3: LIST MANAGEMENT ---
    with tab3:
        st.subheader("Manage Dropdown Lists")
        list_type = st.radio("Select List to Edit:", ["disciplines", "goal_areas"])
        
        with st.form("list_form"):
            new_item = st.text_input(f"Add new item to {list_type}")
            if st.form_submit_button("Add Item"):
                if new_item:
                    upsert_list_item(list_type, new_item)
                    st.rerun()
        
        st.divider()
        items = get_list_data(list_type)
        if not items.empty:
            st.dataframe(items, use_container_width=True, hide_index=True)
            del_item = st.selectbox("Select Item to Delete", [""] + items['name'].tolist())
            if st.button(f"🗑️ Delete Item from {list_type}"):
                if del_item:
                    delete_list_item(list_type, del_item)
                    st.rerun()

    # --- TAB 4: DATABASE REPAIR (MIGRATION TOOLS) ---
    with tab4:
        st.header("🛠️ Data Ownership Migration")
        st.warning("Use this tool to assign old records (with no author) to a specific staff member. This enables the 'Edit' and 'Delete' buttons for those records.")
        
        # Get List of Staff Users
        staff_users = get_list_data("users")
        if not staff_users.empty:
            target_staff = st.selectbox(
                "Select the staff member who should own the old records:", 
                staff_users['username'].tolist(),
                help="Only the owner (author) can edit or delete their own progress notes or session plans."
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.write("### Progress Notes")
                if st.button("🔗 Assign Anonymous Progress Notes"):
                    try:
                        with ENGINE.connect() as conn:
                            # Update records where author is NULL or empty string
                            result = conn.execute(text(
                                "UPDATE progress SET author = :u WHERE author IS NULL OR author = ''"
                            ), {"u": target_staff})
                            conn.commit()
                            st.success(f"Migration Complete: Old progress notes assigned to {target_staff}.")
                    except Exception as e:
                        st.error(f"Error during migration: {e}")

            with col_b:
                st.write("### Session Plans")
                if st.button("📅 Assign Anonymous Session Plans"):
                    try:
                        with ENGINE.connect() as conn:
                            # Update records where author is NULL or empty string
                            result = conn.execute(text(
                                "UPDATE session_plans SET author = :u WHERE author IS NULL OR author = ''"
                            ), {"u": target_staff})
                            conn.commit()
                            st.success(f"Migration Complete: Old session plans assigned to {target_staff}.")
                    except Exception as e:
                        st.error(f"Error during migration: {e}")
        else:
            st.error("No users found to assign records to.")
