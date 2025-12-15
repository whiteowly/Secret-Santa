import sqlite3
import datetime
import logging

DATABASE_NAME = 'santa.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DATABASE_NAME)

def init_db():
    """Initializes the database tables (games and assignments)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Games Table (Stores overall group settings and status)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            group_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL,          -- e.g., 'JOINING', 'COMPLETED'
            date_started TEXT NOT NULL,
            exchange_date TEXT            -- Stores the gift exchange day (from /setdate)
        )
    """)

    # 2. Participants Table (Stores who is in which game)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            first_name TEXT,
            PRIMARY KEY (user_id, group_id)
        )
    """)
    
    # 3. Assignments Table (Stores the draw results: who got who)
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

    # -- Migration: ensure columns exist on existing databases --
    # Some users may have an older 'games' table without 'date_started' or 'exchange_date'.
    cursor.execute("PRAGMA table_info(games)")
    cols = {row[1] for row in cursor.fetchall()}  # row[1] is column name
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
        # Ensure that older rows (created before 'status' existed) get a default status
        conn.execute(
            "UPDATE games SET status = ? WHERE group_id = ? AND (status IS NULL OR status = '')",
            ('JOINING', group_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_game_status(group_id):
    """Returns the current status for the game (e.g., 'JOINING', 'DRAWING', 'COMPLETED')."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT status FROM games WHERE group_id = ?", (group_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    finally:
        conn.close()


def update_game_status(group_id, status):
    """Sets the game's status to the provided value. If the game row doesn't exist, ensure_game_exists should be called first."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE games SET status = ? WHERE group_id = ?", (status, group_id))
        conn.commit()
    finally:
        conn.close()

def add_participant(user_id, group_id, username):
    """Adds a participant to the game. Returns True if added, False if already present."""
    conn = get_db_connection()
    try:
        # Check if participant already exists
        cursor = conn.execute("SELECT 1 FROM participants WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        if cursor.fetchone():
            return False # Already exists

        # If not, insert
        conn.execute("INSERT INTO participants (user_id, group_id, username, first_name) VALUES (?, ?, ?, ?)",
                     (user_id, group_id, username, username)) # Using username for first_name too, for simplicity
        conn.commit()
        return True
    finally:
        conn.close()

def get_participants_data(group_id):
    """Retrieves list of (user_id, username) for the group."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT user_id, username FROM participants WHERE group_id = ?", (group_id,))
        # Returns a list of tuples: [(123, 'Alice'), (456, 'Bob'), ...]
        return cursor.fetchall()
    finally:
        conn.close()

def update_assignments_and_status(group_id, pairs):
    """Saves the draw results (pairs) and updates game status to 'COMPLETED'."""
    conn = get_db_connection()
    try:
        # 1. Clear any previous assignments for this group
        conn.execute("DELETE FROM assignments WHERE group_id = ?", (group_id,))
        
        # 2. Insert new assignments
        assignment_data = [(group_id, santa_id, target_id) for santa_id, target_id in pairs]
        conn.executemany("INSERT INTO assignments (group_id, santa_id, target_id) VALUES (?, ?, ?)", assignment_data)
        
        # 3. Update game status
        conn.execute("UPDATE games SET status = ? WHERE group_id = ?", ('COMPLETED', group_id))
        
        conn.commit()
    finally:
        conn.close()


def try_set_status_to_drawing(group_id):
    """Attempt to set the game's status to 'DRAWING' only if it's currently JOINING/NULL/empty.
    Returns True if the status was changed (meaning this caller won the race), False otherwise.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM games WHERE group_id = ?", (group_id,))
        row = cursor.fetchone()
        current = row[0] if row and row[0] else None
        logging.info(f"try_set_status_to_drawing: group_id={group_id} current_status={current}")
        # Only set to DRAWING if current status indicates JOINING/empty/null
        if current is None or current == '' or (isinstance(current, str) and current.upper().strip() == 'JOINING'):
            cursor.execute("UPDATE games SET status = ? WHERE group_id = ?", ('DRAWING', group_id))
            conn.commit()
            logging.info(f"try_set_status_to_drawing: updated rows={cursor.rowcount}")
            return cursor.rowcount > 0
        else:
            logging.info(f"try_set_status_to_drawing: not updating because status is {current}")
            return False
    finally:
        conn.close()

# --- Functions for Exchange Date ---

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
        # Returns the date text or None
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
        
# --- Add this new function to your database.py file ---

def get_all_assignments_for_user(user_id):
    """
    Retrieves all Secret Santa assignments where the given user_id is the SANTA.
    Returns: A list of tuples: [(group_id, target_name, exchange_date), ...]
    """
    conn = get_db_connection()
    try:
        # We join assignments (santa_id -> target_id), participants (target_id -> target_name), 
        # and games (group_id -> exchange_date).
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
        
        # Returns a list of all assignments found for the user
        return cursor.fetchall()
    finally:
        conn.close()        