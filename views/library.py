# views/library.py
import streamlit as st
import pandas as pd
from .database import add_library_link, get_library, get_list_data, text, ENGINE

def delete_lib_item(item_id):
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM library WHERE id=:id"), {"id":item_id})
        conn.commit()

def show_page():
    st.title("📂 Resource Library")
    
    role = st.session_state.get('role', '').lower()
    child_link = st.session_state.get('child_link')
    username = st.session_state.get('username')

    # --- STAFF/ADMIN: Add New Link ---
    if role in ['admin', 'staff', 'bc', 'ot', 'slp', 'ece']:
        with st.expander("➕ Add New Resource / File Link"):
            with st.form("lib_form"):
                child_df = get_list_data("children")
                targets = ["All"] + (child_df['child_name'].tolist() if not child_df.empty else [])
                
                target = st.selectbox("Assign to", targets)
                title = st.text_input("Title (e.g., Home Exercise Plan)")
                url = st.text_input("Link (Google Drive / Dropbox / Website)")
                category = st.selectbox("Category", ["Homework", "Report", "Video", "Resources", "Other"])
                
                if st.form_submit_button("Post Resource"):
                    if title and url:
                        add_library_link(target, title, url, category, username)
                        st.success("Resource added!")
                        st.rerun()
                    else:
                        st.error("Title and Link are required.")

    # --- DISPLAY LIBRARY ---
    # Determine who we are looking for
    target_child = child_link if role == 'parent' else "All"
    
    # If admin/staff, let them filter
    if role != 'parent':
        child_df = get_list_data("children")
        filter_list = ["All"] + (child_df['child_name'].tolist() if not child_df.empty else [])
        target_child = st.selectbox("View Library For:", filter_list)

    if target_child:
        df = get_library(target_child)
        if not df.empty:
            for cat in df['category'].unique():
                st.subheader(f"📌 {cat}")
                subset = df[df['category'] == cat]
                for _, row in subset.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.markdown(f"[{row['title']}]({row['link_url']})")
                        c1.caption(f"Added by {row['added_by']} on {row['date_added']}")
                        
                        if role in ['admin', 'staff']:
                            if c2.button("Delete", key=f"del_{row['id']}"):
                                delete_lib_item(row['id'])
                                st.rerun()
        else:
            st.info("No resources found.")
