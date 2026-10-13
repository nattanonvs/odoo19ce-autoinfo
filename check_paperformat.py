import psycopg2
conn = psycopg2.connect(dbname='odoo19', user='odoo', password='odoo123', host='localhost')
cur = conn.cursor()

# Check paper format - quote the 'default' column
cur.execute('SELECT id, name, format, margin_top, margin_bottom, margin_left, margin_right, header_spacing, dpi, "default" FROM report_paperformat ORDER BY id')
print("=== Paper Formats ===")
for r in cur.fetchall():
    print(r)

conn.close()
