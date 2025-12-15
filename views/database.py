# views/database.py
import pandas as pd
from datetime import datetime
# NEW IMPORTS FOR POSTGRES
import streamlit as st 
from sqlalchemy import create_engine, text, inspect 
import sqlite3 # Kept for 'get_data' conversion consistency, though only SQLAlchemy is used

# --- CORE DB CONNECTION ---

# Use Streamlit's cache_resource decorator to ensure the connection engine is created only once.
@st.cache_resource
def get_engine():
    """Initializes and returns the SQLAlchemy Engine using Streamlit Secrets."""
    try:
        # 1. Read connection details from secrets.toml
        user = st.secrets["postgres"]["user"]
        password = st.secrets["postgres"]["password"]
        host = st.secrets["postgres"]["host"]
        port = st.secrets["postgres"]["port"]
        database = st.secrets["postgres"]["database"]
        
        # 2. PostgreSQL connection string
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        # 3. Create the engine
        # pool_pre_ping=True helps maintain robust connections over time
        engine = create_engine(db_url, pool_pre_ping=True)
        return engine
    except KeyError:
        st.error("PostgreSQL secrets not found. Please ensure .streamlit/secrets.toml or Streamlit Cloud secrets are configured.")
        return None
    except Exception as e:
        st.error(f"Database connection failed. Please check your credentials. Error: {e}")
        return None

# Global variable for the engine
ENGINE = get_engine()

# --- DDL (Data Definition Language) ---

def init_db():
    """Creates all necessary tables, ensures schema is up-to-date, and populates initial admin/lists."""
    if not ENGINE: return
    
    with ENGINE.connect() as conn:
        
        # 1. Table: Users (Postgres uses PRIMARY KEY on the column itself)
        conn.execute(text('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT, 
            child_link TEXT 
        )'''))
        
        # 2. Table: Children Profiles (Postgres uses SERIAL for auto-increment)
        conn.execute(text('''CREATE TABLE IF NOT EXISTS children (
            id SERIAL PRIMARY KEY,
            child_name TEXT UNIQUE,
            parent_username TEXT, 
            date_of_birth TEXT
        )'''))
        
        # 3. Table: Custom Lists
        conn.execute(text('''CREATE TABLE IF NOT EXISTS disciplines (
            name TEXT UNIQUE
        )'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS goal_areas (
            name TEXT UNIQUE
        )'''))
        
        # 4. Table: Progress Tracker 
        conn.execute(text('''CREATE TABLE IF NOT EXISTS progress (
            id SERIAL PRIMARY KEY,
            date TEXT,
            child_name TEXT,
            discipline TEXT,
            goal_area TEXT,
            status TEXT,
            notes TEXT,
            media_path TEXT 
        )'''))
        
        # 5. Table: Session Plans 
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

        # --- Initial Data Load (Use ON CONFLICT DO NOTHING for IGNORE logic) ---
        conn.execute(text("INSERT INTO users (username, password, role, child_link) VALUES (:u, :p, :r, :c) ON CONFLICT (username) DO NOTHING"),
                     {"u": "adminuser", "p": "admin123", "r": "admin", "c": "All"})
        
        for d in ["OT", "SLP", "BC", "ECE", "Assistant"]:
            conn.execute(text("INSERT INTO disciplines (name) VALUES (:n) ON CONFLICT (name) DO NOTHING"), {"n": d})
            
        for g in ["Regulation", "Communication", "Fine Motor", "Social Play"]:
            conn.execute(text("INSERT INTO goal_areas (name) VALUES (:n) ON CONFLICT (name) DO NOTHING"), {"n": g})
            
        conn.commit()

# --- DML (Data Manipulation Language) ---

# --- User & Login Functions ---

def get_user(username, password):
    """Retrieves user details for login."""
    if not ENGINE: return None
    
    sql_query = text("SELECT username, password, role, child_link FROM users WHERE username = :user AND password = :pass")
    
    with ENGINE.connect() as conn:
        df = pd.read_sql(sql_query, conn, params={"user": username, "pass": password})
    
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def upsert_user(username, password, role, child_link):
    """Inserts or updates a user, prioritizing update if username exists."""
    if not ENGINE: return
    
    # Check if the user exists to decide between UPDATE and INSERT
    user_exists_query = text("SELECT username FROM users WHERE username = :user")
    
    with ENGINE.connect() as conn:
        result = conn.execute(user_exists_query, {"user": username}).fetchone()
        
        if result:
            # User exists, prepare to UPDATE
            # Only update password if one is provided (not empty)
            if password:
                 sql_stmt = text("UPDATE users SET password = :p, role = :r, child_link = :c WHERE username = :u")
                 params = {"u": username, "p": password, "r": role, "c": child_link}
            else:
                 # Update everything but the password
                 sql_stmt = text("UPDATE users SET role = :r, child_link = :c WHERE username = :u")
                 params = {"u": username, "r": role, "c": child_link}
        else:
            # User does not exist, prepare to INSERT
            sql_stmt = text("INSERT INTO users (username, password, role, child_link) VALUES (:u, :p, :r, :c)")
            # New users must have a password
            params = {"u": username, "p": password, "r": role, "c": child_link}
        
        # Execute the statement
        conn.execute(sql_stmt, params)
        conn.commit()

def delete_user(username):
    """Deletes a user account."""
    if not ENGINE: return
    
    sql_stmt = text("DELETE FROM users WHERE username = :u")
    
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"u": username})
        conn.commit()

# --- Child Profile Functions ---

def upsert_child(child_name, parent_username, date_of_birth):
    """Inserts or updates a child profile, using child_name as the unique identifier."""
    if not ENGINE: return
    
    # PostgreSQL uses ON CONFLICT for this logic
    sql_stmt = text("""
        INSERT INTO children (child_name, parent_username, date_of_birth) 
        VALUES (:cn, :pu, :dob)
        ON CONFLICT (child_name) DO UPDATE 
        SET parent_username = EXCLUDED.parent_username, 
            date_of_birth = EXCLUDED.date_of_birth
    """)
    
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {
            "cn": child_name, 
            "pu": parent_username, 
            "dob": date_of_birth
        })
        conn.commit()

def delete_child(child_name):
    """Deletes a child profile."""
    if not ENGINE: return
    
    sql_stmt = text("DELETE FROM children WHERE child_name = :cn")
    
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"cn": child_name})
        conn.commit()

# --- Custom List Functions ---

def get_list_data(table_name):
    """Retrieves all data from a simple list table (e.g., disciplines, goal_areas, users, children)."""
    if not ENGINE: return pd.DataFrame()
    
    # Table name is safe to pass via f-string here as it's not user input.
    with ENGINE.connect() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df

def upsert_list_item(table_name, item_name):
    """Inserts a new item into a list table or does nothing if it exists."""
    if not ENGINE: return
    
    # Use ON CONFLICT DO NOTHING for unique lists
    sql_stmt = text(f"INSERT INTO {table_name} (name) VALUES (:n) ON CONFLICT (name) DO NOTHING")
    
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"n": item_name})
        conn.commit()

def delete_list_item(table_name, item_name):
    """Deletes an item from a list table."""
    if not ENGINE: return
    
    sql_stmt = text(f"DELETE FROM {table_name} WHERE name = :n")
    
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {"n": item_name})
        conn.commit()

# --- Progress/Planner Functions ---

def get_data(table_name):
    """Retrieves all data from a table (Progress or Plans)."""
    if not ENGINE: return pd.DataFrame()
    
    # Table name is safe to pass via f-string here as it's not user input.
    with ENGINE.connect() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df

def save_progress(date, child, discipline, goal, status, notes, media_path):
    """Saves a new progress entry."""
    if not ENGINE: return
    
    sql_stmt = text("""
        INSERT INTO progress (date, child_name, discipline, goal_area, status, notes, media_path) 
        VALUES (:d, :c, :dis, :g, :s, :n, :m)
    """)
    
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {
            "d": date, 
            "c": child, 
            "dis": discipline, 
            "g": goal, 
            "s": status, 
            "n": notes, 
            "m": media_path
        })
        conn.commit()

def save_plan(date, lead_staff, support_staff, warm_up, learning_block, regulation_break, social_play, closing_routine, materials_needed, internal_notes):
    """Saves a new daily session plan entry."""
    if not ENGINE: return
    
    sql_stmt = text("""
        INSERT INTO session_plans (date, lead_staff, support_staff, warm_up, learning_block, regulation_break, social_play, closing_routine, materials_needed, internal_notes) 
        VALUES (:d, :ls, :ss, :wu, :lb, :rb, :sp, :cr, :mn, :in)
    """)
    
    # Format support_staff list into a comma-separated string for TEXT column
    support_staff_str = ", ".join(support_staff)
    
    with ENGINE.connect() as conn:
        conn.execute(sql_stmt, {
            "d": date, 
            "ls": lead_staff, 
            "ss": support_staff_str, # Use the string representation
            "wu": warm_up, 
            "lb": learning_block, 
            "rb": regulation_break, 
            "sp": social_play, 
            "cr": closing_routine, 
            "mn": materials_needed, 
            "in": internal_notes
        })
        conn.commit()
