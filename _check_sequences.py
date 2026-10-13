import psycopg2

conn = psycopg2.connect(host="localhost", dbname="odoo19", user="odoo", password="odoo123")
cur = conn.cursor()

# Check existing sequences with purchase-related prefixes
print("=== Existing sequences (prefix like PR/PB/PT/PI/PF/PD/IT/IB/II) ===")
cur.execute("""
    SELECT id, code, prefix, name, number_next, padding
    FROM ir_sequence
    WHERE prefix IS NOT NULL
    AND (
        prefix LIKE 'PR%' OR prefix LIKE 'PB%' OR prefix LIKE 'PT%'
        OR prefix LIKE 'PI%' OR prefix LIKE 'PF%' OR prefix LIKE 'PD%'
        OR prefix LIKE 'IT%' OR prefix LIKE 'IB%' OR prefix LIKE 'II%'
    )
    ORDER BY prefix
""")
for row in cur.fetchall():
    print(row)

print("\n=== Purchase request sequences ===")
cur.execute("""
    SELECT id, code, prefix, name FROM ir_sequence
    WHERE code LIKE '%purchase.request%' OR code LIKE '%purchase.order%'
    ORDER BY code
""")
for row in cur.fetchall():
    print(row)

# Check if hr.department has pr_sequence_id / po_sequence_id
print("\n=== hr.department fields (pr/po sequence) ===")
cur.execute("""
    SELECT f.name, f.model, t.model
    FROM ir_model_fields f
    JOIN ir_model t ON f.model_id = t.id
    WHERE t.model = 'hr.department'
    AND (f.name LIKE '%sequence%' OR f.name LIKE '%pr_%' OR f.name LIKE '%po_%')
""")
for row in cur.fetchall():
    print(row)

conn.close()
