import psycopg2
conn = psycopg2.connect(dbname='odoo19', user='odoo', password='odoo123', host='localhost')
cur = conn.cursor()
cur.execute("SELECT name, state FROM ir_module_module WHERE name IN ('helpdesk_mgmt','od19_helpdesk_extension','od19_iso_document_control') ORDER BY name")
for r in cur.fetchall():
    print(r)
conn.close()
