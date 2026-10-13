import psycopg2
conn = psycopg2.connect(dbname='odoo19', user='odoo', password='odoo123', host='localhost')
cur = conn.cursor()

# Check for views from od19_helpdesk_extension
cur.execute("SELECT id, name, model, active FROM ir_ui_view WHERE name LIKE '%od19%' OR key LIKE '%od19_helpdesk%' ORDER BY id")
print("=== Views with od19 ===")
for r in cur.fetchall():
    print(r)

# Check module state
cur.execute("SELECT name, state FROM ir_module_module WHERE name LIKE '%helpdesk%' ORDER BY name")
print("\n=== Helpdesk modules ===")
for r in cur.fetchall():
    print(r)

conn.close()
