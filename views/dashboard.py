# views/dashboard.py (UPDATED with CSV Export Function)
import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import date
from .database import get_data, get_list_data 
import os 

# --- NEW: Helper function to convert DataFrame to CSV for export ---
@st.cache_data
def convert_df_to_csv(df):
    # Drop columns that are internal or not useful in an export
    # 'media_path' contains server-local file paths, and 'numeric_status' is only for charting.
    cols_to_drop = [col for col in ['media_path', 'numeric_status'] if col in df.columns]
    # Use errors='ignore' in case 'numeric_status' hasn't been added to the df yet
    df = df.drop(columns=cols_to_drop, errors='ignore') 
    return df.to_csv(index=False).encode('utf-8')
# -----------------------------------------------------------------


def show_page():
    # Retrieve the child filter from the session state (set in app.py during login)
    child_filter = st.session_state.get("child_link", "All")
    user_role = st.session_state.get("user_role", "guest")

    # Fetch data and lists
    try:
        df = get_data("progress")
        
        if df.empty:
            st.warning("No progress data recorded yet. Go to 'Progress Tracker' to add entries.")
            return
            
        # --- FIX: CONVERT DATE COLUMN IMMEDIATELY AFTER FETCHING ---
        # This ensures the 'date' column is a proper datetime object for all user roles.
        df['date'] = pd.to_datetime(df['date']) 
        # ----------------------------------------------------------
        
        # Fetch list of disciplines for the new filter
        disciplines_list = get_list_data("disciplines")["name"].tolist()
    except Exception as e:
        st.error(f"Error loading progress data or lists. Error: {e}")
        return


    # --- Header and Empty Check ---
    if user_role == "parent":
        st.header(f"🏡 My Child's Progress: {child_filter}")
        st.info("This dashboard displays progress data collected by our staff for your child only.")
    else:
        st.header("📊 Clinical Dashboard & Reports")
        st.info("Review program-wide progress or filter by individual child, date, and discipline.")
        
    
    # --- Filtering Logic ---

    # 1. INITIAL FILTER: Handle Parent View
    if child_filter != "All":
        # Parent View: Filter data for their specific child
        df_display = df[df["child_name"] == child_filter].copy()
        if df_display.empty:
            st.warning(f"No progress data found for {child_filter}.")
            return
        selected_child = child_filter
    else:
        # Staff/Admin View: Dynamic Filters
        df_display = df.copy() 
        
        with st.expander("🔎 Filter Data", expanded=True):
            
            # 1. Child Filter (Existing)
            child_list = ["All Children"] + sorted(df_display["child_name"].unique().tolist())
            selected_child = st.selectbox("1. Select Child", child_list)
            
            if selected_child != "All Children":
                df_display = df_display[df_display["child_name"] == selected_child].copy()
            
            # Handle case where the child filter results in empty data before applying date/discipline filters
            if df_display.empty:
                st.warning(f"No progress data found for the selected child: {selected_child}.")
                return
            
            # 2. Date Range Filter
            col_date_start, col_date_end = st.columns(2)

            min_date = df_display['date'].min().date() if not df_display.empty else date.today()
            max_date = df_display['date'].max().date() if not df_display.empty else date.today()

            start_date = col_date_start.date_input("2. Start Date", min_date)
            end_date = col_date_end.date_input("3. End Date", max_date)
            
            if start_date > end_date:
                st.error("Error: Start Date cannot be after End Date.")
                return

            df_display = df_display[
                (df_display['date'].dt.date >= start_date) & 
                (df_display['date'].dt.date <= end_date)
            ].copy()

            # 3. Discipline Filter
            discipline_options = ["All Disciplines"] + disciplines_list
            selected_disciplines = st.multiselect("4. Filter by Discipline", discipline_options, default="All Disciplines")

            if "All Disciplines" not in selected_disciplines:
                df_display = df_display[df_display["discipline"].isin(selected_disciplines)].copy()
            
            
        if df_display.empty:
            st.warning(f"No progress data found matching all selected filters.")
            return

        # --- NEW: CSV Export Button for Staff/Admin ---
        # Determine a dynamic filename based on the filter
        file_filter_name = selected_child.replace(" ", "_") if selected_child != "All Children" else "All_Children"
        
        # Place button in a visible spot
        st.markdown("---")
        st.download_button(
            label="⬇️ Export Filtered Progress Data to CSV",
            data=convert_df_to_csv(df_display.copy()), # Use a copy before sending to the function
            file_name=f'TILP_Progress_Report_{file_filter_name}_{date.today().strftime("%Y%m%d")}.csv',
            mime='text/csv',
            key='download-csv'
        )
        # --- END NEW EXPORT FUNCTIONALITY ---


    # --- Display Metrics and Charts (This part remains the same, operating on filtered data) ---
    
    st.divider()
    
    if selected_child == "All Children":
        st.subheader("Program-Wide Metrics")
    else:
        st.subheader(f"Key Progress Metrics for {selected_child}")
        
    m1, m2, m3 = st.columns(3)
    
    m1.metric("Total Sessions Logged", len(df_display))
    progress_count = len(df_display[df_display["status"] == "Progress"])
    success_rate = round((progress_count / len(df_display)) * 100) if len(df_display) > 0 else 0
    m2.metric("Positive Progress Rate", f"{success_rate}%")
    latest_status = df_display.sort_values(by="date", ascending=False).iloc[0]["status"] if not df_display.empty else "N/A"
    m3.metric("Latest Recorded Status", latest_status)

    # CHARTS
    st.divider()
    
    st.subheader(f"Goal Achievement Trend")
    
    status_map = {"Regression": 1, "Stable": 2, "Progress": 3}
    # Use .loc to avoid SettingWithCopyWarning
    df_display.loc[:, "numeric_status"] = df_display["status"].map(status_map)
    
    fig = px.line(df_display, x="date", y="numeric_status", color="goal_area",
                  title="Status of Goals Over Time (1=Regression, 3=Progress)",
                  markers=True)
    
    fig.update_layout(yaxis=dict(
        tickvals=[1, 2, 3],
        ticktext=["Regression", "Stable", "Progress"],
        title="Performance Status"
    ))
    
    st.plotly_chart(fig, use_container_width=True)

    # --- Recent Notes and Media Display ---
    st.subheader("Recent Notes & Media")
    
    # Iterate through the filtered data and display notes/media
    for index, row in df_display.sort_values(by="date", ascending=False).head(50).iterrows():
        # --- FIX APPLIED: ADDED CHILD NAME TO THE DISPLAY LINE ---
        st.markdown(f"**{row['date'].strftime('%Y-%m-%d')}** | **Child:** **{row['child_name']}** | **{row['discipline']}** | **Goal:** {row['goal_area']} | **Status:** **{row['status']}**")
        st.markdown(f"**Notes:** {row['notes']}")
        
        # Check if media_path is non-null/non-empty and the file exists on the local disk
        if pd.notna(row['media_path']) and row['media_path'] and os.path.exists(row['media_path']):
            file_path = row['media_path']
            # Get the file extension to determine the type
            mime_type = os.path.splitext(file_path)[1].lower()
            
            with st.expander(f"View Attached Media ({os.path.basename(file_path)})"):
                if mime_type in ['.jpg', '.jpeg', '.png']:
                    st.image(file_path, caption="Therapist Media", use_column_width=True)
                elif mime_type in ['.mp4', '.mov']:
                    st.video(file_path, format="video/mp4")
                else:
                    st.warning(f"Media found but cannot display: {os.path.basename(file_path)}")
            
        st.markdown("---")
