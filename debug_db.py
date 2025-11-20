import sqlite3

conn = sqlite3.connect("chat_history.db")
cursor = conn.cursor()

rows = cursor.execute("SELECT * FROM chat_history").fetchall()

for row in rows:
    print(row)

conn.close()
