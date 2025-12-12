import sqlite3
import datetime

DATABASE_NAME = 'santa.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DATABASE_NAME)

def init_db():
    """Initializes the database tables (games and assignments)."""
    conn = get_db_connection()
    cursor = conn.cursor()


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            group_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL,          -- e.g., 'JOINING', 'COMPLETED'
            date_started TEXT NOT NULL,
            exchange_date TEXT            -- Stores the gift exchange day (from /setdate)
        )
    """)

    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            first_name TEXT,
            PRIMARY KEY (user_id, group_id)
        )
    """)
    
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            group_id INTEGER NOT NULL,
            santa_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            PRIMARY KEY (group_id, santa_id),
            FOREIGN KEY (group_id) REFERENCES games(group_id),
            FOREIGN KEY (santa_id) REFERENCES participants(user_id),
            FOREIGN KEY (target_id) REFERENCES participants(user_id)
        )
    """)

    conn.commit()

  
    cursor.execute("PRAGMA table_info(games)")
    cols = {row[1] for row in cursor.fetchall()}
    if 'date_started' not in cols:
        cursor.execute("ALTER TABLE games ADD COLUMN date_started TEXT")
    if 'exchange_date' not in cols:
        cursor.execute("ALTER TABLE games ADD COLUMN exchange_date TEXT")
    if 'status' not in cols:
        cursor.execute("ALTER TABLE games ADD COLUMN status TEXT")
    conn.commit()
    conn.close()

def ensure_game_exists(group_id):
    """Initializes a new game entry if it doesn't exist."""
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO games (group_id, status, date_started) VALUES (?, ?, ?)",
                     (group_id, 'JOINING', datetime.datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def add_participant(user_id, group_id, username):
    """Adds a participant to the game. Returns True if added, False if already present."""
    conn = get_db_connection()
    try:
       
        cursor = conn.execute("SELECT 1 FROM participants WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        if cursor.fetchone():
            return False 

       
        conn.execute("INSERT INTO participants (user_id, group_id, username, first_name) VALUES (?, ?, ?, ?)",
                     (user_id, group_id, username, username)) 
        conn.commit()
        return True
    finally:
        conn.close()

def get_participants_data(group_id):
    """Retrieves list of (user_id, username) for the group."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT user_id, username FROM participants WHERE group_id = ?", (group_id,))
       
        return cursor.fetchall()
    finally:
        conn.close()

def update_assignments_and_status(group_id, pairs):
    """Saves the draw results (pairs) and updates game status to 'COMPLETED'."""
    conn = get_db_connection()
    try:
       
        conn.execute("DELETE FROM assignments WHERE group_id = ?", (group_id,))
      
        assignment_data = [(group_id, santa_id, target_id) for santa_id, target_id in pairs]
        conn.executemany("INSERT INTO assignments (group_id, santa_id, target_id) VALUES (?, ?, ?)", assignment_data)
      
        conn.execute("UPDATE games SET status = ? WHERE group_id = ?", ('COMPLETED', group_id))
        
        conn.commit()
    finally:
        conn.close()



def update_exchange_date(group_id, date_text):
    """Saves the gift exchange date for the game (used by /setdate)."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE games SET exchange_date = ? WHERE group_id = ?", 
                     (date_text, group_id))
        conn.commit()
    finally:
        conn.close()

def get_exchange_date(group_id):
    """Retrieves the saved gift exchange date (used by go_draw_callback)."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT exchange_date FROM games WHERE group_id = ?", (group_id,))
        result = cursor.fetchone()
       
        return result[0] if result and result[0] else None 
    finally:
        conn.close()

def get_exchange_date(group_id):
    """Retrieves the saved gift exchange date text."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT exchange_date FROM games WHERE group_id = ?", (group_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else None 
    finally:
        conn.close()
        


def get_all_assignments_for_user(user_id):
    """
    Retrieves all Secret Santa assignments where the given user_id is the SANTA.
    Returns: A list of tuples: [(group_id, target_name, exchange_date), ...]
    """
    conn = get_db_connection()
    try:
       
        cursor = conn.execute("""
            SELECT
                t1.group_id,
                t2.username,
                t3.exchange_date
            FROM assignments t1
            JOIN participants t2 ON t1.target_id = t2.user_id
            JOIN games t3 ON t1.group_id = t3.group_id
            WHERE t1.santa_id = ?
        """, (user_id,))
        
      
        return cursor.fetchall()
    finally:
        conn.close()        