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
        # Tables with author column included
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
        
        # Standard User and List Tables
        conn.execute(text("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, child_link TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS children (id SERIAL PRIMARY KEY, child_name TEXT UNIQUE, parent_username TEXT, date_of_birth TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS disciplines (name TEXT UNIQUE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS goal_areas (name TEXT UNIQUE)"))
        conn.commit()

# --- Session Plan Logic ---

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

# --- General Data Getters ---
def get_data(table):
    if not ENGINE: return pd.DataFrame()
    with ENGINE.connect() as conn:
        # Dynamic check for missing author column (migration safety)
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

# (Keep your existing get_user, upsert_user, get_attendance_data, save_progress etc. functions here)
