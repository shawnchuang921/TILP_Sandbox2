# app.py (Add new imports and menu items)
from views import tracker, planner, dashboard, admin_tools, billing, schedule, library, communication

# ... inside main() ...

    # 1. Admin Tools
    if user_role == "admin":
        pages["🔑 Admin Tools"] = admin_tools.show_page
        pages["📢 Communication Hub"] = communication.show_page  # NEW
        pages["🗓️ Master Schedule"] = schedule.show_page
        pages["💳 Billing Management"] = billing.show_page

    # 2. Staff Tools
    staff_roles = ["admin", "ot", "slp", "bc", "ece", "assistant", "staff", "therapist"]
    if user_role in staff_roles:
        pages["📝 Progress Tracker"] = tracker.show_page
        pages["📅 Daily Planner"] = planner.show_page
        pages["📂 Resource Library"] = library.show_page  # NEW
        if user_role != "admin": 
             pages["📢 Communication"] = communication.show_page # Staff can send msgs too

    # 3. Parent Tools
    if user_role == "parent":
        pages[f"📊 Dashboard"] = dashboard.show_page
        pages[f"🗓️ Appointments"] = schedule.show_page
        pages[f"📂 File Library"] = library.show_page  # NEW
        pages[f"💳 Billing & Invoices"] = billing.show_page
