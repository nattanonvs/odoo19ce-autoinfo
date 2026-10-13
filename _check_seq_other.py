import psycopg2

conn = psycopg2.connect(host="localhost", dbname="odoo19", user="odoo", password="odoo123")
cur = conn.cursor()

print("=== Odoo 19: Existing sequences for Project, Sale, Accounting, Partner ===")
cur.execute("""
    SELECT code, prefix, name
    FROM ir_sequence
    WHERE code IS NOT NULL
    AND (
        code LIKE '%project%' OR code LIKE '%sale%' OR code LIKE '%quotation%'
        OR code LIKE '%account%' OR code LIKE '%partner%' OR code LIKE '%res.partner%'
        OR code LIKE '%journal%' OR code LIKE '%invoice%' OR code LIKE '%payment%'
        OR code LIKE '%billing%' OR code LIKE '%advance%' OR code LIKE '%petty%'
        OR code LIKE '%cheque%' OR code LIKE '%vat%' OR code LIKE '%wht%'
        OR code LIKE '%tax%' OR code LIKE '%cash%' OR code LIKE '%asset%'
        OR code LIKE '%revision%' OR code LIKE '%task%'
    )
    ORDER BY code
""")
for row in cur.fetchall():
    print(f"  {row[0]:40s} | prefix={str(row[1]):20s} | {row[2]}")

print("\n=== Odoo 19: ir.sequence with prefixes (custom od19 only) ===")
cur.execute("""
    SELECT code, prefix, name FROM ir_sequence
    WHERE code LIKE 'od19.%'
    ORDER BY code
""")
for row in cur.fetchall():
    print(f"  {row[0]:40s} | prefix={str(row[1]):20s} | {row[2]}")

conn.close()
