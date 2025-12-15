import sqlite3
import sys

def inspect(group_id):
    conn = sqlite3.connect('santa.db')
    cur = conn.cursor()
    print('=== GAMES ===')
    cur.execute('SELECT group_id, status, date_started, exchange_date FROM games WHERE group_id = ?', (group_id,))
    rows = cur.fetchall()
    if not rows:
        print('NO GAME ROW FOR', group_id)
    for r in rows:
        print(repr(r))
    print('\n=== PARTICIPANTS ===')
    cur.execute('SELECT user_id, username, first_name FROM participants WHERE group_id = ?', (group_id,))
    for r in cur.fetchall():
        print(repr(r))
    print('\n=== ASSIGNMENTS ===')
    cur.execute('SELECT group_id, santa_id, target_id FROM assignments WHERE group_id = ?', (group_id,))
    for r in cur.fetchall():
        print(repr(r))
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: inspect_db.py <group_id>')
        sys.exit(1)
    inspect(int(sys.argv[1]))
