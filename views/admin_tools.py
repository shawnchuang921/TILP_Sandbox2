# views/admin_tools.py
import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import date, timedelta
from .database import (
    ENGINE, 
    get_list_data, 
    get_data
)

# --- DATABASE HELPER FUNCTIONS ---
def upsert_user(username, password, role, child_link):
    with ENGINE.connect() as conn:
        result = conn.execute(text("SELECT username FROM users WHERE username = :u"), {"u": username}).fetchone()
        if result:
            if password:
                sql = text("UPDATE users SET password=:p, role=:r, child_link=:c WHERE username=:u")
                conn.execute(sql, {"u": username, "p": password, "r": role, "c": child_link})
            else:
                sql = text("UPDATE users SET role=:r, child_link=:c WHERE username=:u")
                conn.execute(sql, {"u": username, "r": role, "c": child_link})
        else:
            conn.execute(text("INSERT INTO users (username, password, role, child_link) VALUES (:u, :p, :r, :c)"), 
                         {"u": username, "p": password, "r": role, "c": child_link})
        conn.commit()

def delete_user(username):
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
        conn.commit()

def upsert_child(cn, pu, dob):
    with ENGINE.connect() as conn:
        conn.execute(text("""
            INSERT INTO children (child_name, parent_username, date_of_birth) 
            VALUES (:cn, :pu, :dob) 
            ON CONFLICT (child_name) 
            DO UPDATE SET parent_username=EXCLUDED.parent_username, date_of_birth=EXCLUDED.date_of_birth
        """), {"cn": cn, "pu": pu, "dob": dob})
        conn.commit()

def delete_child(cn):
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM children WHERE child_name = :cn"), {"cn": cn})
        conn.commit()

def upsert_attendance(date_val, child_name, status, logged_by):
    with ENGINE.connect() as conn:
        conn.execute(text("""
            INSERT INTO attendance (date, child_name, status, logged_by) 
            VALUES (:d, :cn, :s, :lb)
            ON CONFLICT (date, child_name) 
            DO UPDATE SET status = EXCLUDED.status, logged_by = EXCLUDED.logged_by
        """), {"d": str(date_val), "cn": child_name, "s": status, "lb": logged_by})
        conn.commit()

def upsert_list_item(table, item):
    with ENGINE.connect() as conn:
        conn.execute(text(f"INSERT INTO {table} (name) VALUES (:n) ON CONFLICT (name) DO NOTHING"), {"n": item})
        conn.commit()

def delete_list_item(table, item):
    with ENGINE.connect() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE name = :n"), {"n": item})
        conn.commit()

# --- MAIN PAGE VIEW ---
def show_page():
    st.title("🔑 Admin & Operations Control")
    username = st.session_state.get("username", "Admin")
    
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Users", "👶 Children", "📅 Attendance", "⚙️ Lists"])

    # --- TAB 1: USER MANAGEMENT ---
    with tab1:
        st.subheader("Manage Users")
        with st.expander("➕ Add / Update User"):
            with st.form("user_form", clear_on_submit=True):
                u = st.text_input("Username")
                p = st.text_input("Password")
                r = st.selectbox("Role", ["admin", "ot", "slp", "bc", "ece", "assistant", "staff", "parent"])
                c_df = get_list_data("children")
                c_list = ["None"] + (c_df['child_name'].tolist() if not c_df.empty else [])
                cl = st.selectbox("Link to Child", c_list)
                if st.form_submit_button("Save User"):
                    upsert_user(u, p, r, (cl if cl != "None" else ""))
                    st.success(f"User {u} saved!")
                    st.rerun()
        df_u = get_data("users")
        st.dataframe(df_u, use_container_width=True)

    # --- TAB 2: CHILD PROFILES ---
    with tab2:
        st.subheader("Child Directory")
        with st.form("child_form", clear_on_submit=True):
            cn = st.text_input("Child Name")
            pu = st.text_input("Parent Username")
            dob = st.text_input("DOB (YYYY-MM-DD)")
            if st.form_submit_button("Save Child"):
                upsert_child(cn, pu, dob)
                st.rerun()
        df_c = get_list_data("children")
        st.dataframe(df_c, use_container_width=True)

    # --- TAB 3: ATTENDANCE (FIXED & FILTERABLE) ---
    with tab3:
        st.subheader("Attendance Tracking")
        
        # 1. MARK ATTENDANCE
        with st.expander("📝 Mark Today's Attendance"):
            with st.form("att_form", clear_on_submit=True):
                att_date = st.date_input("Date", date.today())
                children_list = get_list_data("children")['child_name'].tolist()
                sel_child = st.selectbox("Select Child", children_list)
                att_status = st.radio("Status", ["Present", "Absent", "Late", "Excused"], horizontal=True)
                if st.form_submit_button("Submit Attendance"):
                    upsert_attendance(att_date, sel_child, att_status, username)
                    st.success(f"Logged {sel_child} as {att_status}")
                    st.rerun()

        st.divider()
        
        # 2. REVIEW & FILTER ATTENDANCE
        st.subheader("Review Attendance Records")
        c1, c2 = st.columns(2)
        start_date = c1.date_input("From Date", date.today() - timedelta(days=7))
        end_date = c2.date_input("To Date", date.today())
        
        with ENGINE.connect() as conn:
            att_df = pd.read_sql(text("SELECT * FROM attendance ORDER BY date DESC"), conn)
        
        if not att_df.empty:
            # Convert to date objects for filtering
            att_df['date_dt'] = pd.to_datetime(att_df['date']).dt.date
            filtered_att = att_df[(att_df['date_dt'] >= start_date) & (att_df['date_dt'] <= end_date)]
            
            if not filtered_att.empty:
                st.dataframe(filtered_att.drop(columns=['date_dt']), use_container_width=True, hide_index=True)
                
                # Simple stats
                total_days = len(filtered_att)
                presents = len(filtered_att[filtered_att['status'] == 'Present'])
                st.info(f"Summary for period: {presents} Presents out of {total_days} total logs.")
            else:
                st.warning("No records found for this date range.")
        else:
            st.info("No attendance records found in database.")

    # --- TAB 4: APP LISTS ---
    with tab4:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Disciplines")
            new_d = st.text_input("Add Discipline")
            if st.button("Add D"):
                upsert_list_item("disciplines", new_d)
                st.rerun()
            d_df = get_list_data("disciplines")
            st.dataframe(d_df)
        with col2:
            st.subheader("Goal Areas")
            new_g = st.text_input("Add Goal Area")
            if st.button("Add G"):
                upsert_list_item("goal_areas", new_g)
                st.rerun()
            g_df = get_list_data("goal_areas")
            st.dataframe(g_df)
