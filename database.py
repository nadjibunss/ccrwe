import sqlite3
import datetime
import os
import re

DB_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_verified INTEGER DEFAULT 0
                )''')

    # Numbers table
    # status: 0=AVAILABLE, 1=ALLOCATED, 2=DEAD/USED
    c.execute('''CREATE TABLE IF NOT EXISTS numbers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT UNIQUE,
                    country TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assigned_to INTEGER, 
                    assigned_at TIMESTAMP,
                    status INTEGER DEFAULT 0
                )''')
                
    # Settings/Config table (key-value)
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )''')

    # Check and Add otp_count column if not exists
    try:
        c.execute("SELECT otp_count FROM numbers LIMIT 1")
    except sqlite3.OperationalError:
        print("Migrating DB: Adding otp_count to numbers table...")
        c.execute("ALTER TABLE numbers ADD COLUMN otp_count INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_NAME)

# --- USER OPERATIONS ---
def add_user(user_id, username, first_name):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", 
                  (user_id, username, first_name))
        conn.commit()
    finally:
        conn.close()

def is_user_verified(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT is_verified FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 1

def set_user_verified(user_id, status=1):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET is_verified=? WHERE user_id=?", (status, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_total_users_count():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

# --- NUMBER OPERATIONS ---
def add_numbers_bulk(numbers_list):
    """
    numbers_list: list of tuples (phone_number, country)
    """
    conn = get_connection()
    c = conn.cursor()
    added_count = 0
    try:
        for num, country in numbers_list:
            clean_num = re.sub(r'\D', '', str(num))
            try:
                c.execute("INSERT INTO numbers (phone_number, country, status, otp_count) VALUES (?, ?, 0, 0)", (clean_num, country))
                added_count += 1
            except sqlite3.IntegrityError:
                # Check if it exists but is USED (Status 2)
                c.execute("SELECT status FROM numbers WHERE phone_number=?", (clean_num,))
                row = c.fetchone()
                if row and row[0] == 2:
                    # It was used/dead. Recycle it! (Delete & Insert to move to bottom)
                    c.execute("DELETE FROM numbers WHERE phone_number=?", (clean_num,))
                    c.execute("INSERT INTO numbers (phone_number, country, status, otp_count) VALUES (?, ?, 0, 0)", (clean_num, country))
                    added_count += 1
                else:
                    continue # Real duplicate (Status 0 or 1)
        conn.commit()
    finally:
        conn.close()
    return added_count

def check_stock_duplicates(numbers_list):
    """
    Analyzes a list of (phone, country) tuples.
    Returns: (unique_list, duplicates_count)
    """
    conn = get_connection()
    c = conn.cursor()
    
    unique_new = []
    duplicates_count = 0
    
    existing_phones = set()
    try:
        c.execute("SELECT phone_number FROM numbers WHERE status=0")
        existing_phones = {row[0] for row in c.fetchall()}
    except: pass
    
    for num, country in numbers_list:
        clean_num = re.sub(r'\D', '', str(num))
        if clean_num in existing_phones:
            duplicates_count += 1
        else:
            unique_new.append((clean_num, country))
            
    conn.close()
    return unique_new, duplicates_count

def get_available_numbers_count(country=None):
    conn = get_connection()
    c = conn.cursor()
    if country:
        c.execute("SELECT COUNT(*) FROM numbers WHERE status=0 AND country=?", (country,))
    else:
        c.execute("SELECT COUNT(*) FROM numbers WHERE status=0")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_available_countries():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT country, COUNT(*) FROM numbers WHERE status=0 GROUP BY country")
    results = c.fetchall()
    conn.close()
    return results # [(CountryA, 100), (CountryB, 50)]

def delete_country_stock(country):
    """Delete only available numbers for a specific country."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM numbers WHERE country=? AND status=0", (country,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

    return deleted

def release_and_rotate_numbers(user_id):
    """
    Releases numbers currently assigned to user.
    - If OTP received (otp_count > 0) -> Mark as USED (Status 2).
    - If NO OTP (otp_count == 0) -> Rotate (Delete & Re-insert at end).
    """
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT id, phone_number, country, otp_count FROM numbers WHERE status=1 AND assigned_to=?", (user_id,))
    rows = c.fetchall()
    
    for row in rows:
        num_id, phone, country, count = row
        # Ensure count is treated as int
        count = int(count) if count else 0
        
        if count > 0:
            # Worked -> Mark as USED (Status 2)
            c.execute("UPDATE numbers SET status=2, assigned_to=NULL, assigned_at=NULL WHERE id=?", (num_id,))
        else:
            # Failed -> Rotate (Delete and Re-insert to end)
            c.execute("DELETE FROM numbers WHERE id=?", (num_id,))
            # Re-insert as new Available number (Status 0)
            c.execute("INSERT INTO numbers (phone_number, country, status, otp_count) VALUES (?, ?, 0, 0)", (phone, country))

    conn.commit()
    conn.close()

def allocate_numbers(user_id, count=2, country=None):
    """
    Allocates 'count' sequential numbers to user_id, optionally filtered by country.
    First releases/rotates any currently held numbers.
    """
    # 1. Release & Rotate existing numbers for this user
    release_and_rotate_numbers(user_id)

    conn = get_connection()
    c = conn.cursor()
    
    # Fetch available numbers
    if country:
        c.execute("SELECT id, phone_number, country FROM numbers WHERE status=0 AND country=? ORDER BY id ASC LIMIT ?", (country, count))
    else:
        c.execute("SELECT id, phone_number, country FROM numbers WHERE status=0 ORDER BY id ASC LIMIT ?", (count,))
        
    rows = c.fetchall()
    
    allocated = []
    if len(rows) < count:
        conn.close()
        return [] # Not enough stock
        
    for row in rows:
        num_id, num_val, country_val = row
        c.execute("UPDATE numbers SET status=1, assigned_to=?, assigned_at=CURRENT_TIMESTAMP WHERE id=?", (user_id, num_id))
        allocated.append((num_val, country_val))
        
    conn.commit()
    conn.close()
    return allocated

def get_user_active_numbers(user_id):
    """Get numbers currently assigned to user for OTP checking"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT phone_number, country FROM numbers WHERE assigned_to=? AND status=1", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_stats(user_id):
    """Get count of numbers used by user, grouped by country."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT country, COUNT(*) FROM numbers WHERE assigned_to=? GROUP BY country", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def find_owner_of_number(phone_number):
    conn = get_connection()
    c = conn.cursor()
    clean_num = re.sub(r'\D', '', str(phone_number))
    # Use LIKE for partial match (suffix) since input might be masked
    c.execute("SELECT assigned_to FROM numbers WHERE phone_number LIKE ? AND status=1", ('%' + clean_num,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def increment_otp_count(phone_number):
    conn = get_connection()
    c = conn.cursor()
    # Use partial match for masked numbers
    clean_num = re.sub(r'\D', '', str(phone_number))
    c.execute("UPDATE numbers SET otp_count = otp_count + 1 WHERE phone_number LIKE ?", ('%' + clean_num,))
    conn.commit()
    conn.close()

# --- SETTINGS OPERATIONS ---
def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default
