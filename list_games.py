import sqlite3

conn = sqlite3.connect('santa.db')
cur = conn.cursor()
cur.execute('SELECT group_id, status, date_started, exchange_date FROM games')
rows = cur.fetchall()
print('GAMES ROWS COUNT:', len(rows))
for r in rows:
    print(repr(r))
conn.close()
