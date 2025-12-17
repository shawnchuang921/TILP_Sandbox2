# views/tracker.py
import streamlit as st
import pandas as pd
from datetime import datetime
import views.database as db
import os

def show_progress_input():
    st.subheader("Log Progress")

    # --- 1. Check for Edit Mode ---
    # We check if the user clicked "Edit" in the view section below
    is_edit_mode = st.session_state.get('edit_mode', False)
    edit_data = st.session_state.get('edit_data', {})

    if is_edit_mode:
        st.info(f"✏️ Editing entry for {edit_data.get('child_name')} (ID: {edit_data.get('id')})")

    # --- 2. Input Fields ---
    
    # Date Input
    default_date = datetime.now()
    if is_edit_mode and 'date' in edit_data:
        try:
            default_date = datetime.strptime(edit_data['date'], '%Y-%m-%d')
        except:
            pass # Use today if parsing fails

    date = st.date_input("Date", value=default_date)

    # Child Selection
    children_df = db.get_list_data("children")
    child_options = children_df['child_name'].tolist() if not children_df.empty else []
    
    # Set default index for child if editing
    child_index = None
    if is_edit_mode and edit_data.get('child_name') in child_options:
        child_index = child_options.index(edit_data.get('child_name'))

    child = st.selectbox("Child", child_options, index=child_index, placeholder="Select Child")

    # Discipline Selection (Filtered by Role)
    user_role = st.session_state.get('role', '')
    discipline_df = db.get_list_data("disciplines")
    all_disciplines = discipline_df['name'].tolist() if not discipline_df.empty else []

    if user_role == 'admin':
        # Admin sees all options
        discipline_options = all_disciplines
        disc_index = None
        # If editing, try to match the existing discipline
        if is_edit_mode and edit_data.get('discipline') in discipline_options:
            disc_index = discipline_options.index(edit_data.get('discipline'))
    else:
        # Therapists only see their own role (assuming role matches discipline name)
        # If the role isn't in the list (e.g., specific naming mismatch), show all as fallback
        if user_role in all_disciplines:
            discipline_options = [user_role]
            disc_index = 0
        else:
            discipline_options = all_disciplines
            disc_index = None
            
    discipline = st.selectbox("Discipline", discipline_options, index=disc_index, placeholder="Select Discipline")

    # Goal Area
    goals_df = db.get_list_data("goal_areas")
    goal_options = goals_df['name'].tolist() if not goals_df.empty else []
    
    goal_index = None
    if is_edit_mode and edit_data.get('goal_area') in goal_options:
        goal_index = goal_options.index(edit_data.get('goal_area'))

    goal_area = st.selectbox("Goal Area", goal_options, index=goal_index, placeholder="Select Goal Area")

    # Status
    status_options = ["Met", "Partially Met", "Not Met", "Not Attempted"]
    status_index = None
    if is_edit_mode and edit_data.get('status') in status_options:
        status_index = status_options.index(edit_data.get('status'))
        
    status = st.selectbox("Status", status_options, index=status_index)

    # Notes
    notes_default = edit_data.get('notes', "") if is_edit_mode else ""
    notes = st.text_area("Clinical Notes", value=notes_default)

    # Media Upload
    # Note: Media files are not easily re-populated in file_uploader during edit
    # We will keep the old path if no new file is uploaded
    uploaded_file = st.file_uploader("Upload Photo/Video (Optional)", type=['png', 'jpg', 'jpeg', 'mp4', 'mov'])

    # --- 3. Save / Update Action ---
    
    # Change button label based on mode
    btn_label = "Update Progress" if is_edit_mode else "Save Progress"

    if st.button(btn_label, type="primary"):
        if not child or not discipline or not goal_area:
            st.error("Please fill in all required fields (Child, Discipline, Goal Area).")
        else:
            # Handle Media Path
            media_path = edit_data.get('media_path', None) if is_edit_mode else None
            
            if uploaded_file:
                # Save locally (temporary for now until cloud storage is added)
                os.makedirs("media", exist_ok=True)
                # Create a unique filename to prevent overwrites
                import uuid
                ext = uploaded_file.name.split('.')[-1]
                filename = f"{uuid.uuid4()}.{ext}"
                save_path = os.path.join("media", filename)
                
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                media_path = save_path

            # Save Logic
            if is_edit_mode:
                # Update existing entry
                db.update_progress(
                    id=edit_data['id'],
                    date=date.strftime('%Y-%m-%d'),
                    child=child,
                    discipline=discipline,
                    goal=goal_area,
                    status=status,
                    notes=notes,
                    media_path=media_path
                )
                st.success("Entry updated successfully!")
                # Exit edit mode
                st.session_state.edit_mode = False
                st.session_state.edit_data = {}
                st.rerun()
            else:
                # Create new entry
                current_author = st.session_state.get('username', 'Unknown')
                db.save_progress(
                    date=date.strftime('%Y-%m-%d'),
                    child=child,
                    discipline=discipline,
                    goal=goal_area,
                    status=status,
                    notes=notes,
                    media_path=media_path,
                    author=current_author
                )
                st.success("Progress entry saved successfully!")

    # Cancel Edit Button
    if is_edit_mode:
        if st.button("Cancel Edit"):
            st.session_state.edit_mode = False
            st.session_state.edit_data = {}
            st.rerun()

def show_progress_data():
    st.markdown("---")
    st.subheader("Progress History")

    # Get Data
    progress_data = db.get_data("progress")
    
    if progress_data.empty:
        st.info("No progress entries found.")
        return

    # Sort by date descending
    progress_data = progress_data.sort_values(by="date", ascending=False).reset_index(drop=True)
    
    # Current User Details for Permissions
    current_user = st.session_state.get('username', '')
    current_role = st.session_state.get('role', '')

    # --- Display Loop ---
    for index, row in progress_data.iterrows():
        # Determine Permissions
        # Admin can edit anything. Users can only edit their own entries.
        is_author = (row.get('author') == current_user)
        is_admin = (current_role == 'admin')
        can_modify = is_author or is_admin

        # Card / Expander styling
        label = f"{row['date']} | {row['child_name']} ({row['discipline']})"
        with st.expander(label):
            col_info, col_media = st.columns([2, 1])
            
            with col_info:
                st.markdown(f"**Goal:** {row['goal_area']}")
                st.markdown(f"**Status:** {row['status']}")
                st.markdown(f"**Notes:** {row['notes']}")
                st.caption(f"Logged by: {row.get('author', 'Unknown')}")
            
            with col_media:
                if row['media_path'] and os.path.exists(row['media_path']):
                    if row['media_path'].endswith(('.mp4', '.mov')):
                        st.video(row['media_path'])
                    else:
                        st.image(row['media_path'])
            
            # --- Edit / Delete Actions ---
            if can_modify:
                st.markdown("---")
                c1, c2 = st.columns([1, 4])
                
                with c1:
                    # EDIT BUTTON
                    if st.button("✏️ Edit", key=f"edit_{row['id']}"):
                        st.session_state.edit_mode = True
                        st.session_state.edit_data = row.to_dict()
                        st.rerun() # Rerun to refresh the Input section above
                
                with c2:
                    # DELETE BUTTON
                    # We use a nested check to confirm deletion to avoid accidents
                    if st.button("🗑️ Delete", key=f"del_btn_{row['id']}"):
                        st.session_state[f"confirm_del_{row['id']}"] = True
                        st.rerun()

                # Confirmation Box for Delete
                if st.session_state.get(f"confirm_del_{row['id']}", False):
                    st.warning("Are you sure you want to delete this?")
                    conf_c1, conf_c2 = st.columns(2)
                    with conf_c1:
                        if st.button("Yes, Delete", key=f"yes_del_{row['id']}"):
                            db.delete_progress(row['id'])
                            st.success("Deleted!")
                            del st.session_state[f"confirm_del_{row['id']}"]
                            st.rerun()
                    with conf_c2:
                        if st.button("Cancel", key=f"no_del_{row['id']}"):
                            del st.session_state[f"confirm_del_{row['id']}"]
                            st.rerun()
