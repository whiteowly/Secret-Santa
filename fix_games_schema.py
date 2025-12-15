import sqlite3

conn = sqlite3.connect('santa.db')
cur = conn.cursor()
print('Dropping malformed games table if exists...')
cur.execute('DROP TABLE IF EXISTS games')
print('Recreating games table with clean schema...')
cur.execute('''
CREATE TABLE games (
    group_id INTEGER PRIMARY KEY,
    status TEXT,
    date_started TEXT,
    exchange_date TEXT
)
''')
conn.commit()
print('Done')
conn.close()
