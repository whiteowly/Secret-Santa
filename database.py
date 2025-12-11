import sqlite3
import logging

# Configuration for the database file
DB_NAME = 'santa.db'
logging.basicConfig(level=logging.INFO)

# --- Connection Management ---

def get_db_connection():
    """Returns a new connection object for thread-safe database access."""
    # Using sqlite3.connect is best practice when opening and closing for single transactions
    return sqlite3.connect(DB_NAME)

# --- Initialization ---

def init_db():
    """Initializes the database and creates the necessary tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Table 1: Games (Manages the overall Secret Santa event in a group)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                group_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,          -- e.g., 'JOINING', 'COMPLETED'
                date_started TEXT NOT NULL
            )
        """)
        
        # Table 2: Participants
        # target_id is initially NULL and filled after the draw
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                username TEXT,
                target_id INTEGER,
                
                PRIMARY KEY (user_id, group_id), 
                FOREIGN KEY (group_id) REFERENCES games(group_id)
            )
        """)
        
        conn.commit()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Database Initialization Error: {e}")
    finally:
        conn.close()

# --- CRUD (Create, Read, Update, Delete) Operations ---

def ensure_game_exists(group_id):
    """Creates a new game entry if one doesn't exist for the group."""
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO games (group_id, status, date_started) VALUES (?, ?, DATETIME('now'))", 
                     (group_id, 'JOINING'))
        conn.commit()
    finally:
        conn.close()

def add_participant(user_id, group_id, username):
    """Adds a participant if they don't already exist for the given game."""
    conn = get_db_connection()
    try:
        # The 'OR IGNORE' handles users clicking the join button multiple times
        conn.execute("INSERT OR IGNORE INTO participants (user_id, group_id, username) VALUES (?, ?, ?)", 
                     (user_id, group_id, username))
        conn.commit()
        return True
    except Exception:
        return False # Failed to add/already exists (though OR IGNORE minimizes this)
    finally:
        conn.close()

def get_participant_count(group_id):
    """Retrieves the total number of unique participants in a game."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT COUNT(user_id) FROM participants WHERE group_id = ?", (group_id,))
        return cursor.fetchone()[0]
    finally:
        conn.close()
        
def get_participants_data(group_id):
    """Retrieves a list of all participants' user_id and username for the draw."""
    conn = get_db_connection()
    try:
        # Order by user_id to ensure the order is consistent before and after shuffle
        cursor = conn.execute("SELECT user_id, username FROM participants WHERE group_id = ? ORDER BY user_id", (group_id,))
        # Returns a list of tuples: [(user_id, username), ...]
        return cursor.fetchall()
    finally:
        conn.close()

def update_assignments_and_status(group_id, assignments):
    """
    Updates the 'target_id' for each participant and sets the game status to COMPLETED.
    Args: assignments: list of (santa_id, target_id) tuples.
    """
    conn = get_db_connection()
    try:
        # Use a transaction for multiple updates (better performance and atomicity)
        
        # Update each participant's target_id
        update_data = [(target_id, santa_id, group_id) for santa_id, target_id in assignments]
        conn.executemany("UPDATE participants SET target_id = ? WHERE user_id = ? AND group_id = ?", update_data)
        
        # Update the game status
        conn.execute("UPDATE games SET status = ? WHERE group_id = ?", ('COMPLETED', group_id))
        
        conn.commit()
    finally:
        conn.close()