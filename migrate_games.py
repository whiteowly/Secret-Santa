import sqlite3

conn = sqlite3.connect('santa.db')
cur = conn.cursor()

# Find all group_ids from participants and assignments
cur.execute('SELECT DISTINCT group_id FROM participants')
parts = {r[0] for r in cur.fetchall()}
cur.execute('SELECT DISTINCT group_id FROM assignments')
assn = {r[0] for r in cur.fetchall()}
all_groups = parts.union(assn)
print('Groups discovered:', all_groups)

for gid in sorted(all_groups):
    cur.execute('SELECT 1 FROM games WHERE group_id = ?', (gid,))
    if cur.fetchone():
        print(f'Game row exists for {gid}')
        continue
    # Determine status: if assignments exist, mark COMPLETED else JOINING
    cur.execute('SELECT 1 FROM assignments WHERE group_id = ?', (gid,))
    status = 'COMPLETED' if cur.fetchone() else 'JOINING'
    from datetime import datetime
    cur.execute('INSERT INTO games (group_id, status, date_started) VALUES (?, ?, ?)',
                (gid, status, datetime.now().isoformat()))
    print(f'Inserted game row for {gid} with status {status}')

conn.commit()
conn.close()
