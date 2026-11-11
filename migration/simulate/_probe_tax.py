# -*- coding: utf-8 -*-
import os, sys
_ID = os.path.join(os.getcwd(), 'migration', 'import')
if _ID not in sys.path:
    sys.path.insert(0, _ID)
import legacy  # noqa: E402

print('=== od15 account_move columns matching tax_invoice/invoice ===')
rows = legacy.fetch_all(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_name='account_move' AND (column_name LIKE '%tax_invoice%' "
    "   OR column_name LIKE '%invoice%') ORDER BY column_name")
for r in rows:
    print('  %-30s %s' % (r['column_name'], r['data_type']))

print()
print('=== sample values for a posted in_invoice ===')
rows = legacy.fetch_all(
    "SELECT id, name, ref, date, invoice_date, is_tax_invoice "
    "FROM account_move WHERE name='APTH2602-0095' LIMIT 1")
for r in rows:
    print(' ', r)

print()
print('=== od19 taxes named 7% ===')
for t in env['account.tax'].search([('name', '=', '7%')]):
    print('  id=%-5s use=%-9s amount=%-5s repartition_account=%s'
          % (t.id, t.type_tax_use, t.amount,
             [(r.repartition_type, r.account_id.code) for r in t.invoice_repartition_line_ids]))
