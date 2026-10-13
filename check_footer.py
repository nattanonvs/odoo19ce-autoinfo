import psycopg2
conn = psycopg2.connect(dbname='odoo19', user='odoo', password='odoo123', host='localhost')
cur = conn.cursor()

# Check company report_footer
cur.execute("SELECT id, name, report_footer FROM res_company")
print("=== Companies ===")
for r in cur.fetchall():
    print(f"ID: {r[0]}, Name: {r[1]}")
    print(f"  report_footer: {r[2]}")

# Check report action paperformat
cur.execute("SELECT id, name, paperformat_id FROM ir_act_report_xml WHERE model = 'sale.order' AND report_name = 'sale.report_saleorder'")
print("\n=== Sale Order Report ===")
for r in cur.fetchall():
    print(r)

conn.close()
