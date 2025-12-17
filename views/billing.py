# views/billing.py
import streamlit as st
import pandas as pd
from datetime import date
from .database import get_invoices, create_invoice, get_list_data, update_invoice_status, delete_invoice

def show_page():
    st.title("💳 Billing & Invoices")
    
    role = st.session_state.get('role', '').lower()
    child_link = st.session_state.get('child_link')

    # --- ADMIN VIEW: Create & Manage ---
    if role == 'admin':
        col_create, col_manage = st.columns(2)
        
        # 1. Create
        with col_create.expander("➕ Create Invoice", expanded=False):
            with st.form("inv_form"):
                i_date = st.date_input("Date", date.today())
                child_df = get_list_data("children")
                children = child_df['child_name'].tolist() if not child_df.empty else []
                selected_child = st.selectbox("Child", children)
                desc = st.text_input("Description")
                amount = st.number_input("Amount ($)", min_value=0.0, step=10.0)
                status = st.selectbox("Status", ["Unpaid", "Paid", "Overdue"])
                note = st.text_area("Notes")
                if st.form_submit_button("Generate"):
                    create_invoice(i_date, selected_child, desc, amount, status, note)
                    st.success("Created!")
                    st.rerun()

        # 2. Manage (Edit/Delete)
        with col_manage.expander("🛠️ Manage Invoices", expanded=False):
            st.info("Refer to the 'ID' in the table below.")
            inv_id = st.number_input("Invoice ID to modify", min_value=1, step=1)
            action = st.radio("Action", ["Update Status", "Delete Invoice"], horizontal=True)
            
            if action == "Update Status":
                new_stat = st.selectbox("New Status", ["Paid", "Unpaid", "Overdue"])
                if st.button("Update Status"):
                    update_invoice_status(inv_id, new_stat)
                    st.success(f"Invoice {inv_id} updated.")
                    st.rerun()
            else:
                if st.button("🗑️ Delete Permanently", type="primary"):
                    delete_invoice(inv_id)
                    st.warning(f"Invoice {inv_id} deleted.")
                    st.rerun()
        
        st.divider()

    # --- PARENT/LIST VIEW ---
    df = pd.DataFrame()
    
    if role == 'parent':
        if child_link and child_link not in ["None", "All"]:
            df = get_invoices(child_name=child_link)
            st.subheader(f"Financial Overview for {child_link}")
        else:
            st.error("No child linked.")
    elif role == 'admin':
        child_df = get_list_data("children")
        search_list = ["All"] + (child_df['child_name'].tolist() if not child_df.empty else [])
        search_child = st.selectbox("Filter by Child", search_list)
        if search_child != "All":
            df = get_invoices(child_name=search_child)
        else:
            df = get_invoices()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Summary
        unpaid = df[df['status'] == 'Unpaid']['amount'].sum()
        overdue = df[df['status'] == 'Overdue']['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Due", f"${unpaid:,.2f}")
        c2.metric("Overdue", f"${overdue:,.2f}", delta_color="inverse")
        c3.metric("Total History", f"${df['amount'].sum():,.2f}")
        
        st.write("### 🧾 Invoice History")
        # Ensure 'id' is shown for Admin so they can use the Modify tool
        cols = ['date', 'item_desc', 'amount', 'status', 'note']
        if role == 'admin':
            cols.insert(0, 'id')
            
        st.dataframe(df[cols].sort_values('date', ascending=False), use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Statement", csv, "Statement.csv", "text/csv")
    else:
        st.info("No billing records.")
