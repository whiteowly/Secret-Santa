import sqlite3
conn=sqlite3.connect('santa.db')
cur=conn.cursor()
try:
    cur.execute("PRAGMA table_info(games)")
    rows=cur.fetchall()
    if not rows:
        print('NO games TABLE')
    else:
        for r in rows:
            print(r)
except Exception as e:
    print('ERR',e)
finally:
    conn.close()
