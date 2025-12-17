# views/billing.py
import streamlit as st
import pandas as pd
from datetime import date
from .database import get_invoices, create_invoice, get_list_data

def show_page():
    st.title("💳 Billing & Invoices")
    
    role = st.session_state.get('role', '').lower()
    child_link = st.session_state.get('child_link')

    # --- ADMIN VIEW: Create Invoices ---
    if role == 'admin':
        with st.expander("➕ Create New Charge / Invoice"):
            with st.form("inv_form"):
                i_date = st.date_input("Date", date.today())
                
                # Child Selector
                child_df = get_list_data("children")
                children = child_df['child_name'].tolist() if not child_df.empty else []
                selected_child = st.selectbox("Child", children)
                
                desc = st.text_input("Description (e.g. November Tuition)")
                amount = st.number_input("Amount ($)", min_value=0.0, step=10.0)
                status = st.selectbox("Status", ["Unpaid", "Paid", "Overdue"])
                note = st.text_area("Notes (Optional)")
                
                if st.form_submit_button("Generate Charge"):
                    create_invoice(i_date, selected_child, desc, amount, status, note)
                    st.success("Invoice created successfully!")
                    st.rerun()
        st.divider()

    # --- PARENT VIEW: Financial Dashboard ---
    
    # Filter: Parents see only their child; Admins can see all
    df = pd.DataFrame()
    
    if role == 'parent':
        if child_link and child_link not in ["None", "All"]:
            df = get_invoices(child_name=child_link)
            st.subheader(f"Financial Overview for {child_link}")
        else:
            st.error("No child linked to account.")
    elif role == 'admin':
        # Admin Filter
        child_df = get_list_data("children")
        search_list = ["All"] + (child_df['child_name'].tolist() if not child_df.empty else [])
        search_child = st.selectbox("Filter by Child (Admin View)", search_list)
        
        if search_child != "All":
            df = get_invoices(child_name=search_child)
        else:
            df = get_invoices()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # 1. Summary Metrics
        unpaid = df[df['status'] == 'Unpaid']['amount'].sum()
        overdue = df[df['status'] == 'Overdue']['amount'].sum()
        total = df['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Due", f"${unpaid:,.2f}")
        c2.metric("Overdue", f"${overdue:,.2f}", delta_color="inverse")
        c3.metric("Total History", f"${total:,.2f}")
        
        # 2. Invoice List
        st.write("### 🧾 Invoice History")
        st.dataframe(
            df[['date', 'item_desc', 'amount', 'status', 'note']].sort_values('date', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        # 3. Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Statement (CSV)", csv, "Statement.csv", "text/csv")
        
    else:
        st.info("No billing records found.")
