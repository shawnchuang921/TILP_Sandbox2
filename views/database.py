# views/database.py (FINAL VERSION - Including all features and delete_attendance)
import pandas as pd
from datetime import datetime
import streamlit as st 
from sqlalchemy import create_engine, text, inspect 
import sqlite3 

# --- CORE DB CONNECTION ---

@st.cache_resource
def get_engine():
    """Initializes and returns the SQLAlchemy Engine using Streamlit Secrets."""
    try:
        user = st.secrets["postgres"]["user"]
        password = st.secrets["postgres"]["password"]
        host = st.secrets["postgres"]["host"]
        port = st.secrets["postgres"]["port"]
        database = st.secrets["postgres"]["database"]
        
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(db_url, pool_pre_ping=True)
        return engine
    except KeyError:
        st.error("PostgreSQL secrets not found. Please ensure .streamlit/secrets.toml or Streamlit Cloud secrets are configured.")
        return None
    except Exception as e:
        st.error(f"Database connection failed. Please check your credentials. Error: {e}")
        return None

ENGINE = get_engine()

# --- DDL (Data Definition Language) ---

def init_db():
    """Creates all necessary tables and ensures schema is up-to-date."""
    if not ENGINE: return
    
    with ENGINE.connect() as conn:
        conn.execute(text('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT, 
            child_link TEXT 
        )'''))
        
        conn.execute(text('''CREATE TABLE IF NOT EXISTS children (
            id SERIAL PRIMARY KEY,
            child_name TEXT UNIQUE,
            parent_username TEXT, 
            date_of_birth TEXT
        )'''))
        
        conn.execute(text('''CREATE TABLE IF NOT EXISTS disciplines (
            name TEXT UNIQUE
        )'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS goal_areas (
            name TEXT UNIQUE
        )'''))
        
        conn.execute(text('''CREATE TABLE IF NOT EXISTS progress (
            id SERIAL PRIMARY KEY,
            date TEXT,
            child_name TEXT,
            discipline TEXT,
            goal_area TEXT,
            status TEXT,
            notes TEXT,
            media_path TEXT,
            author TEXT
        )'''))
        
        conn.execute(text('''CREATE TABLE IF NOT EXISTS session_plans (
            id SERIAL PRIMARY KEY,
            date TEXT,
            lead_staff TEXT,
            support_staff TEXT,
            warm_up TEXT,
            learning_block TEXT,
            regulation_break TEXT,
            social_play TEXT,
            closing_routine TEXT,
            materials_needed TEXT,
            internal_notes TEXT
        )'''))

        # --- NEW: ATTENDANCE TABLE ---
        conn.execute(text('''CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            date TEXT,
            child_name TEXT,
            status TEXT, 
            logged_by TEXT,
            UNIQUE (date, child_name)
        )'''))


        # Initial Data Load
        conn.execute(text("INSERT INTO users (username, password, role, child_link) VALUES (:u, :p, :r, :c) ON CONFLICT (username) DO NOTHING"),
                     {"u": "adminuser", "p": "admin123", "r": "admin", "c": "All"})
        
        # Add default disciplines/roles
        for d in ["OT", "SLP", "BC", "ECE", "Assistant"]:
            conn.execute(text("INSERT INTO disciplines (name) VALUES (:n) ON CONFLICT (name) DO NOTHING"), {"n": d})
            
        # Add default goal areas
        for g in ["Regulation", "Communication", "Fine Motor", "Social Play"]:
            conn.execute(text("INSERT INTO goal_areas (name) VALUES (:n) ON CONFLICT (name) DO NOTHING"), {"n": g})
            
        conn.commit()

# --- DML (Data Manipulation Language) ---

# --- User & Login Functions ---

def get_user(username, password):
    if not ENGINE: return None
    sql_query = text("SELECT username, password, role, child_link FROM users WHERE username = :user AND password = :pass")
    with ENGINE.connect() as conn:
        df = pd.read_sql(sql_query, conn, params={"user": username, "pass": password})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def get_user_discipline(username):
    """Retrieves the discipline (role) of the current user."""
    if not ENGINE: return None
    sql_query = text("SELECT role FROM users WHERE username = :user")
    with ENGINE.connect() as conn:
        result = conn.execute(sql_query, {"user": username}).fetchone()
    if result:
        return result[0]
    return None

def upsert_user(username, password, role, child_link):
    if not ENGINE: return
    user_exists_query = text("SELECT username FROM users WHERE username = :user")
    with ENGINE.connect() as conn:
        result = conn.execute(user_exists_query, {"user": username}).fetchone()
        if result:
            if password:
                 sql_stmt = text("UPDATE users SET password = :p, role = :r, child_link = :c WHERE username = :u")
                 params = {"u": username, "p": password, "r": role, "c": child_link}
            else:
                 sql_stmt = text("UPDATE users SET role = :r, child_link = :c WHERE username = :u")
                 params = {"u": username, "r": role, "c": child_link}
        else:
            sql_stmt = text("INSERT INTO users (username, password, role, child_link) VALUES (:u, :p, :r, :c)")
            params = {"u": username, "p": password, "r": role, "c": child_link}
        conn.execute(sql_stmt, params)
        conn.commit()

def delete_user(username):
    if not ENGINE: return
    sql_stmt = text("DELETE FROM users WHERE username = :u")
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"u": username})
        conn.commit()

# --- Child Profile Functions ---

def upsert_child(child_name, parent_username, date_of_birth):
    if not ENGINE: return
    sql_stmt = text("""
        INSERT INTO children (child_name, parent_username, date_of_birth) 
        VALUES (:cn, :pu, :dob)
        ON CONFLICT (child_name) DO UPDATE 
        SET parent_username = EXCLUDED.parent_username, 
            date_of_birth = EXCLUDED.date_of_birth
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"cn": child_name, "pu": parent_username, "dob": date_of_birth})
        conn.commit()

def delete_child(child_name):
    if not ENGINE: return
    sql_stmt = text("DELETE FROM children WHERE child_name = :cn")
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"cn": child_name})
        conn.commit()

# --- Custom List Functions ---

def get_list_data(table_name):
    if not ENGINE: return pd.DataFrame()
    with ENGINE.connect() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df

def upsert_list_item(table_name, item_name):
    if not ENGINE: return
    sql_stmt = text(f"INSERT INTO {table_name} (name) VALUES (:n) ON CONFLICT (name) DO NOTHING")
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"n": item_name})
        conn.commit()

def delete_list_item(table_name, item_name):
    if not ENGINE: return
    sql_stmt = text(f"DELETE FROM {table_name} WHERE name = :n")
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"n": item_name})
        conn.commit()

# --- Progress/Planner Functions ---

def get_data(table_name):
    """Retrieves all data from a table (Progress or Plans)."""
    if not ENGINE: return pd.DataFrame()
    
    # Simple retrieval for session_plans
    if table_name != "progress":
        with ENGINE.connect() as conn:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        return df

    # Progress table: ensure 'author' column exists before reading
    try:
         with ENGINE.connect() as conn:
             inspector = inspect(ENGINE)
             columns = [c['name'] for c in inspector.get_columns('progress')]
             if 'author' not in columns:
                  conn.execute(text("ALTER TABLE progress ADD COLUMN author TEXT"))
                  conn.commit()
             
             df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
             return df
    except Exception as e:
        # Fallback if connection or query fails
        st.warning(f"Error accessing 'progress' table: {e}")
        return pd.DataFrame()


def save_progress(date, child, discipline, goal, status, notes, media_path, author):
    """Saves a new progress entry, including the author."""
    if not ENGINE: return
    sql_stmt = text("""
        INSERT INTO progress (date, child_name, discipline, goal_area, status, notes, media_path, author) 
        VALUES (:d, :c, :dis, :g, :s, :n, :m, :a)
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {
            "d": date, "c": child, "dis": discipline, "g": goal, 
            "s": status, "n": notes, "m": media_path, "a": author
        })
        conn.commit()

def update_progress(id, date, child, discipline, goal, status, notes, media_path):
    """Updates an existing progress entry. Author is not updated."""
    if not ENGINE: return
    sql_stmt = text("""
        UPDATE progress 
        SET date = :d, child_name = :c, discipline = :dis, goal_area = :g, 
            status = :s, notes = :n, media_path = :m
        WHERE id = :id
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {
            "id": id, "d": date, "c": child, "dis": discipline, 
            "g": goal, "s": status, "n": notes, "m": media_path
        })
        conn.commit()

def delete_progress(id):
    """Deletes a progress entry by ID."""
    if not ENGINE: return
    sql_stmt = text("DELETE FROM progress WHERE id = :id")
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"id": id})
        conn.commit()

def save_plan(date, lead_staff, support_staff, warm_up, learning_block, regulation_break, social_play, closing_routine, materials_needed, internal_notes):
    """Saves a new daily session plan entry."""
    if not ENGINE: return
    sql_stmt = text("""
        INSERT INTO session_plans (date, lead_staff, support_staff, warm_up, learning_block, regulation_break, social_play, closing_routine, materials_needed, internal_notes) 
        VALUES (:d, :ls, :ss, :wu, :lb, :rb, :sp, :cr, :mn, :in)
    """)
    support_staff_str = ", ".join(support_staff)
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {
            "d": date, "ls": lead_staff, "ss": support_staff_str, 
            "wu": warm_up, "lb": learning_block, "rb": regulation_break, 
            "sp": social_play, "cr": closing_routine, "mn": materials_needed, "in": internal_notes
        })
        conn.commit()

# --- Attendance Functions (NEW) ---

def upsert_attendance(date, child_name, status, logged_by):
    """Inserts or updates a daily attendance record."""
    if not ENGINE: return
    sql_stmt = text("""
        INSERT INTO attendance (date, child_name, status, logged_by) 
        VALUES (:d, :cn, :s, :lb)
        ON CONFLICT (date, child_name) DO UPDATE 
        SET status = EXCLUDED.status, 
            logged_by = EXCLUDED.logged_by;
    """)
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {
            "d": date, "cn": child_name, "s": status, "lb": logged_by
        })
        conn.commit()

def get_attendance_data(date=None, child_name=None):
    """Retrieves attendance data, filtered by date or child."""
    if not ENGINE: return pd.DataFrame()
    
    query = "SELECT * FROM attendance"
    params = {}
    
    if date and child_name:
        query += " WHERE date = :d AND child_name = :cn"
        params = {"d": date, "cn": child_name}
    elif date:
        query += " WHERE date = :d"
        params = {"d": date}
    elif child_name:
        query += " WHERE child_name = :cn ORDER BY date DESC"
        params = {"cn": child_name}
    else:
        # No filters, order by date descending
        query += " ORDER BY date DESC"

    with ENGINE.connect() as conn:
        df = pd.read_sql_query(text(query), conn, params=params)
    return df

def delete_attendance(id):
    """Deletes an attendance entry by ID."""
    if not ENGINE: return
    sql_stmt = text("DELETE FROM attendance WHERE id = :id")
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"id": id})
        conn.commit()
