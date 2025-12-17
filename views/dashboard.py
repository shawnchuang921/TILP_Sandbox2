# views/dashboard.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from .database import get_list_data, get_data, upsert_attendance, get_attendance_data, delete_attendance

def show_page():
    st.title("📊 Program Dashboard")
    
    user_role = st.session_state.get('role', 'staff')
    username = st.session_state.get('username')
    child_link = st.session_state.get('child_link')

    # --- PARENT VIEW ---
    if user_role == 'parent':
        st.subheader(f"👋 Welcome! Attendance Overview for {child_link}")
        
        if not child_link or child_link == "None":
            st.warning("Your account is not yet linked to a child profile. Please contact the administrator.")
            return

        # Date Filter for Parents
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date", date.today() - timedelta(days=30))
        end_date = col2.date_input("End Date", date.today())

        # Fetch Data
        df_att = get_attendance_data(child_name=child_link)

        if not df_att.empty:
            # Convert and Filter
            df_att['date'] = pd.to_datetime(df_att['date']).dt.date
            df_filtered = df_att[(df_att['date'] >= start_date) & (df_att['date'] <= end_date)]
            
            if not df_filtered.empty:
                # Calculate Stats
                total_days = len(df_filtered)
                present_days = len(df_filtered[df_filtered['status'] == 'Present'])
                absent_days = len(df_filtered[df_filtered['status'] == 'Absent'])
                
                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Days Logged", total_days)
                m2.metric("Days Present", present_days)
                m3.metric("Days Absent", absent_days)

                st.divider()
                st.write("### Detailed Attendance Log")
                st.dataframe(
                    df_filtered[['date', 'status']].sort_values('date', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No attendance records found for this date range.")
        else:
            st.info("No attendance records found for your child yet.")

    # --- STAFF/ADMIN VIEW ---
    else:
        st.subheader("📋 Staff Attendance Management")
        
        # Attendance Entry Form
        with st.expander("➕ Log Today's Attendance", expanded=False):
            with st.form("att_form"):
                att_date = st.date_input("Date", date.today())
                child_df = get_list_data("children")
                
                if not child_df.empty:
                    selected_child = st.selectbox("Child", child_df['child_name'].tolist())
                    status = st.radio("Status", ["Present", "Absent", "Late"], horizontal=True)
                    
                    if st.form_submit_button("Submit Attendance"):
                        upsert_attendance(att_date.isoformat(), selected_child, status, username)
                        st.success(f"Attendance logged for {selected_child}")
                        st.rerun()
                else:
                    st.error("No children profiles found.")

        st.divider()
        
        # Staff Search/Filter
        st.write("### All Attendance Records")
        df_all = get_attendance_data()
        
        if not df_all.empty:
            # Filter by child or date
            staff_col1, staff_col2 = st.columns(2)
            filter_child = staff_col1.selectbox("Filter by Child", ["All"] + list(df_all['child_name'].unique()))
            
            df_display = df_all.copy()
            if filter_child != "All":
                df_display = df_display[df_display['child_name'] == filter_child]
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Admin Delete Function
            if user_role == 'admin':
                del_id = st.number_input("Enter ID to Delete", min_value=0, step=1)
                if st.button("🗑️ Delete Record"):
                    delete_attendance(del_id)
                    st.rerun()
        else:
            st.info("No records found.")
