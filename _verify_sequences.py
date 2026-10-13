import psycopg2

conn = psycopg2.connect(host="localhost", dbname="odoo19", user="odoo", password="odoo123")
cur = conn.cursor()

print("=== ISO Document Sequences created ===")
cur.execute("""
    SELECT code, prefix, name, number_next, padding
    FROM ir_sequence
    WHERE code LIKE 'od19.%'
    ORDER BY code
""")
for row in cur.fetchall():
    print(f"  {row[0]:20s} | prefix={row[1]:6s} | {row[2]}")

# Check hr.department has the new fields
print("\n=== hr.department new fields ===")
cur.execute("""
    SELECT f.name FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'hr.department' AND f.name IN ('pr_sequence_id', 'po_sequence_id')
""")
for row in cur.fetchall():
    print(f"  {row[0]}")

# Check purchase.request has department_id
print("\n=== purchase.request department_id field ===")
cur.execute("""
    SELECT f.name FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'purchase.request' AND f.name = 'department_id'
""")
for row in cur.fetchall():
    print(f"  {row[0]}")

# Check purchase.order has department_id
print("\n=== purchase.order department_id field ===")
cur.execute("""
    SELECT f.name FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'purchase.order' AND f.name = 'department_id'
""")
for row in cur.fetchall():
    print(f"  {row[0]}")

conn.close()
