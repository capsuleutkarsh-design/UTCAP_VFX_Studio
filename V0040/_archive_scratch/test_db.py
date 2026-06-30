import sqlite3
conn=sqlite3.connect(r'C:\Users\utkarsh.tripathi.SQUADVFX-26\AppData\Local\UTVFX\ut_vfx.db')
print(conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='stock_library'").fetchone()[0])
