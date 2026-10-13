import psycopg2

conn = psycopg2.connect(host="localhost", dbname="postgres", user="odoo", password="odoo123")
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
for row in cur.fetchall():
    print(row[0])
conn.close()
