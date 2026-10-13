import psycopg2

conn = psycopg2.connect(host="localhost", dbname="odoo19", user="odoo", password="odoo123")
cur = conn.cursor()

print("=== Odoo 19: hr.department sequence fields ===")
cur.execute("""
    SELECT f.name FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'hr.department' AND f.name LIKE '%sequence%'
    ORDER BY f.name
""")
for row in cur.fetchall():
    print(f"  {row[0]}")

print("\n=== Odoo 19: res.users sequence fields ===")
cur.execute("""
    SELECT f.name FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'res.users' AND f.name LIKE '%sequence%'
    ORDER BY f.name
""")
for row in cur.fetchall():
    print(f"  {row[0]}")

print("\n=== Odoo 19: project.project custom fields ===")
cur.execute("""
    SELECT f.name FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'project.project' AND f.name LIKE 'od19%'
    ORDER BY f.name
""")
for row in cur.fetchall():
    print(f"  {row[0]}")

print("\n=== Odoo 19: project.task custom fields ===")
cur.execute("""
    SELECT f.name FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'project.task' AND (f.name LIKE 'od19%' OR f.name = 'code')
    ORDER BY f.name
""")
for row in cur.fetchall():
    print(f"  {row[0]}")

print("\n=== Odoo 19: analytic.account fields ===")
cur.execute("""
    SELECT f.name FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'account.analytic.account' AND f.name LIKE 'od19%'
    ORDER BY f.name
""")
for row in cur.fetchall():
    print(f"  {row[0]}")

conn.close()
