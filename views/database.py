# views/database.py
import pandas as pd
from datetime import datetime
import streamlit as st
from sqlalchemy import create_engine, text, inspect

@st.cache_resource
def get_engine():
    try:
        user = st.secrets["postgres"]["user"]
        password = st.secrets["postgres"]["password"]
        host = st.secrets["postgres"]["host"]
        port = st.secrets["postgres"]["port"]
        database = st.secrets["postgres"]["database"]
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

ENGINE = get_engine()

def init_db():
    if not ENGINE: return
    with ENGINE.connect() as conn:
        # --- EXISTING TABLES (DO NOT TOUCH) ---
        conn.execute(text('''CREATE TABLE IF NOT EXISTS progress (
            id SERIAL PRIMARY KEY, date TEXT, child_name TEXT, discipline TEXT, 
            goal_area TEXT, status TEXT, notes TEXT, media_path TEXT, author TEXT)'''))
        
        conn.execute(text('''CREATE TABLE IF NOT EXISTS session_plans (
            id SERIAL PRIMARY KEY, date TEXT, lead_staff TEXT, support_staff TEXT, 
            warm_up TEXT, learning_block TEXT, regulation_break TEXT, social_play TEXT, 
            closing_routine TEXT, materials_needed TEXT, internal_notes TEXT, author TEXT)'''))

        conn.execute(text('''CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY, date TEXT, child_name TEXT, status TEXT, 
            logged_by TEXT, UNIQUE (date, child_name))'''))
        
        conn.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, child_link TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS children (id SERIAL PRIMARY KEY, child_name TEXT UNIQUE, parent_username TEXT, date_of_birth TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS disciplines (name TEXT UNIQUE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS goal_areas (name TEXT UNIQUE)"))
        
        # --- NEW TABLES FOR BILLING & SCHEDULE ---
        conn.execute(text('''CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY, date TEXT, child_name TEXT, 
            item_desc TEXT, amount REAL, status TEXT, note TEXT)'''))
            
        conn.execute(text('''CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY, date TEXT, time TEXT, child_name TEXT, 
            discipline TEXT, staff TEXT, cost REAL, status TEXT)'''))
            
        conn.commit()

# --- AUTHENTICATION & USERS ---

def get_user(username, password):
    if not ENGINE: return None
    sql_query = text("SELECT username, password, role, child_link FROM users WHERE username = :user AND password = :pass")
    with ENGINE.connect() as conn:
        df = pd.read_sql(sql_query, conn, params={"user": username, "pass": password})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def upsert_user(username, password, role, child_link):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        result = conn.execute(text("SELECT username FROM users WHERE username = :u"), {"u": username}).fetchone()
        if result:
            if password:
                sql = text("UPDATE users SET password=:p, role=:r, child_link=:c WHERE username=:u")
                params = {"u": username, "p": password, "r": role, "c": child_link}
            else:
                sql = text("UPDATE users SET role=:r, child_link=:c WHERE username=:u")
                params = {"u": username, "r": role, "c": child_link}
        else:
            sql = text("INSERT INTO users (username, password, role, child_link) VALUES (:u, :p, :r, :c)")
            params = {"u": username, "p": password, "r": role, "c": child_link}
        conn.execute(sql, params)
        conn.commit()

def delete_user(username):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
        conn.commit()

# --- DATA RETRIEVAL ---

def get_data(table):
    if not ENGINE: return pd.DataFrame()
    with ENGINE.connect() as conn:
        inspector = inspect(ENGINE)
        cols = [c['name'] for c in inspector.get_columns(table)]
        if 'author' not in cols and table in ['progress', 'session_plans']:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN author TEXT"))
            conn.commit()
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)

def get_list_data(table):
    if not ENGINE: return pd.DataFrame()
    with ENGINE.connect() as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)

# --- PROGRESS TRACKER ---

def save_progress(date, child, discipline, goal, status, notes, media_path, author):
    if not ENGINE: return
    sql = text("""
        INSERT INTO progress (date, child_name, discipline, goal_area, status, notes, media_path, author) 
        VALUES (:d, :c, :dis, :g, :s, :n, :m, :a)
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql, {"d": date, "c": child, "dis": discipline, "g": goal, "s": status, "n": notes, "m": media_path, "a": author})
        conn.commit()

def update_progress(id, date, child, discipline, goal, status, notes, media_path):
    if not ENGINE: return
    sql = text("""
        UPDATE progress SET date=:d, child_name=:c, discipline=:dis, goal_area=:g, 
        status=:s, notes=:n, media_path=:m WHERE id=:id
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql, {"id": id, "d": date, "c": child, "dis": discipline, "g": goal, "s": status, "n": notes, "m": media_path})
        conn.commit()

def delete_progress(progress_id):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM progress WHERE id = :id"), {"id": progress_id})
        conn.commit()

# --- ATTENDANCE ---

def upsert_attendance(date, child_name, status, logged_by):
    if not ENGINE: return
    sql = text("""
        INSERT INTO attendance (date, child_name, status, logged_by) 
        VALUES (:d, :cn, :s, :lb)
        ON CONFLICT (date, child_name) DO UPDATE 
        SET status = EXCLUDED.status, logged_by = EXCLUDED.logged_by
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql, {"d": date, "cn": child_name, "s": status, "lb": logged_by})
        conn.commit()

def get_attendance_data(date=None, child_name=None):
    if not ENGINE: return pd.DataFrame()
    query = "SELECT * FROM attendance"
    params = {}
    if date:
        query += " WHERE date = :d"
        params["d"] = date
    elif child_name:
        query += " WHERE child_name = :cn ORDER BY date DESC"
        params["cn"] = child_name
    else:
        query += " ORDER BY date DESC"
    with ENGINE.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)

def delete_attendance(att_id):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM attendance WHERE id = :id"), {"id": att_id})
        conn.commit()

# --- SESSION PLANS ---

def save_plan(date, lead, support, wu, lb, rb, sp, cr, mn, notes, author):
    if not ENGINE: return
    sql = text("""INSERT INTO session_plans (date, lead_staff, support_staff, warm_up, learning_block, 
                  regulation_break, social_play, closing_routine, materials_needed, internal_notes, author) 
                  VALUES (:d, :ls, :ss, :wu, :lb, :rb, :sp, :cr, :mn, :in, :a)""")
    ss_str = ", ".join(support) if isinstance(support, list) else str(support)
    with ENGINE.connect() as conn:
        conn.execute(sql, {"d": date, "ls": lead, "ss": ss_str, "wu": wu, "lb": lb, "rb": rb, "sp": sp, "cr": cr, "mn": mn, "in": notes, "a": author})
        conn.commit()

def update_plan(plan_id, date, lead, support, wu, lb, rb, sp, cr, mn, notes):
    if not ENGINE: return
    sql = text("""UPDATE session_plans SET date=:d, lead_staff=:ls, support_staff=:ss, warm_up=:wu, 
                  learning_block=:lb, regulation_break=:rb, social_play=:sp, closing_routine=:cr, 
                  materials_needed=:mn, internal_notes=:in WHERE id=:id""")
    ss_str = ", ".join(support) if isinstance(support, list) else str(support)
    with ENGINE.connect() as conn:
        conn.execute(sql, {"id": plan_id, "d": date, "ls": lead, "ss": ss_str, "wu": wu, "lb": lb, "rb": rb, "sp": sp, "cr": cr, "mn": mn, "in": notes})
        conn.commit()

def delete_plan(plan_id):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM session_plans WHERE id = :id"), {"id": plan_id})
        conn.commit()

# --- OTHER HELPERS ---

def upsert_child(cn, pu, dob):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        conn.execute(text("INSERT INTO children (child_name, parent_username, date_of_birth) VALUES (:cn, :pu, :dob) ON CONFLICT (child_name) DO UPDATE SET parent_username=EXCLUDED.parent_username, date_of_birth=EXCLUDED.date_of_birth"), {"cn": cn, "pu": pu, "dob": dob})
        conn.commit()

def delete_child(cn):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM children WHERE child_name = :cn"), {"cn": cn})
        conn.commit()

def upsert_list_item(table, item):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        conn.execute(text(f"INSERT INTO {table} (name) VALUES (:n) ON CONFLICT (name) DO NOTHING"), {"n": item})
        conn.commit()

def delete_list_item(table, item):
    if not ENGINE: return
    with ENGINE.connect() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE name = :n"), {"n": item})
        conn.commit()

# --- NEW FUNCTIONS: BILLING & SCHEDULE ---

def create_invoice(date, child, item, amount, status, note):
    if not ENGINE: return
    sql = text("""
        INSERT INTO invoices (date, child_name, item_desc, amount, status, note) 
        VALUES (:d, :c, :i, :a, :s, :n)
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql, {"d": date, "c": child, "i": item, "a": amount, "s": status, "n": note})
        conn.commit()

def get_invoices(child_name=None):
    if not ENGINE: return pd.DataFrame()
    query = "SELECT * FROM invoices"
    params = {}
    if child_name:
        query += " WHERE child_name = :c"
        params["c"] = child_name
    query += " ORDER BY date DESC"
    with ENGINE.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)

def create_appointment(date, time, child, discipline, staff, cost, status):
    if not ENGINE: return
    sql = text("""
        INSERT INTO appointments (date, time, child_name, discipline, staff, cost, status)
        VALUES (:d, :t, :c, :dis, :st, :co, :stat)
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql, {"d": date, "t": time, "c": child, "dis": discipline, "st": staff, "co": cost, "stat": status})
        conn.commit()

def get_appointments(child_name=None):
    if not ENGINE: return pd.DataFrame()
    query = "SELECT * FROM appointments"
    params = {}
    if child_name:
        query += " WHERE child_name = :c"
        params["c"] = child_name
    query += " ORDER BY date DESC, time ASC"
    with ENGINE.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)
