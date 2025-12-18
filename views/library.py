# views/library.py
import streamlit as st
from .database import add_library_link, get_library, get_list_data, ENGINE, text

def delete_lib_item(item_id):
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM library WHERE id=:id"), {"id":item_id})
        conn.commit()

def show_page():
    st.title("📂 Resource Library")
    role = st.session_state.get('role', '')
    username = st.session_state.get('username')
    child_link = st.session_state.get('child_link')

    # ADMIN/STAFF: Ability to upload/add links
    if role != "parent":
        with st.expander("➕ Add New File Link or Resource"):
            with st.form("add_resource_form", clear_on_submit=True):
                child_df = get_list_data("children")
                targets = ["All"] + (child_df['child_name'].tolist() if not child_df.empty else [])
                
                target_child = st.selectbox("Assign to Child", targets)
                title = st.text_input("Resource Title (e.g., OT Home Exercises)")
                link = st.text_input("URL Link (Google Drive, Dropbox, etc.)")
                cat = st.selectbox("Category", ["Homework", "Reports", "Educational", "Videos"])
                
                if st.form_submit_button("Add to Library"):
                    if title and link:
                        add_library_link(target_child, title, link, cat, username)
                        st.success("Resource added successfully!")
                        st.rerun()
                    else:
                        st.error("Please provide both a title and a link.")

    st.divider()

    # VIEWING LOGIC
    view_target = child_link if role == "parent" else "All"
    
    if role != "parent":
        child_df = get_list_data("children")
        names = ["All"] + (child_df['child_name'].tolist() if not child_df.empty else [])
        view_target = st.selectbox("View Library For:", names)

    df = get_library(view_target)
    
    if not df.empty:
        for category in df['category'].unique():
            st.subheader(f"📁 {category}")
            cat_df = df[df['category'] == category]
            for _, row in cat_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**[{row['title']}]({row['link_url']})**")
                    c1.caption(f"Added by {row['added_by']} on {row['date_added']}")
                    if role == "admin":
                        if c2.button("🗑️", key=f"del_lib_{row['id']}"):
                            delete_lib_item(row['id'])
                            st.rerun()
    else:
        st.info("No resources available for this selection.")
