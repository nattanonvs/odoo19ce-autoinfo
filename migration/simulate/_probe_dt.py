# -*- coding: utf-8 -*-
import os, sys
_ID = os.path.join(os.getcwd(), 'migration', 'import')
if _ID not in sys.path:
    sys.path.insert(0, _ID)
import legacy  # noqa: E402

rows = legacy.fetch_all(
    "SELECT l.display_type, count(*) AS n FROM account_move_line l "
    "JOIN account_move m ON m.id=l.move_id "
    "WHERE m.state='posted' AND m.date BETWEEN '2026-01-01' AND '2026-08-31' "
    "GROUP BY l.display_type ORDER BY 2 DESC")
print('=== od15 display_type distribution ===')
for r in rows:
    print('  %-15r %s' % (r['display_type'], r['n']))

print()
print('=== sample out_invoice IV17590 lines ===')
rows = legacy.fetch_all(
    "SELECT l.id, a.code, l.name, l.debit, l.credit, l.display_type, l.product_id, "
    "       l.quantity, l.price_unit, l.discount, l.tax_line_id "
    "FROM account_move_line l JOIN account_account a ON a.id=l.account_id "
    "JOIN account_move m ON m.id=l.move_id WHERE m.name='IV17590' ORDER BY l.id")
for r in rows:
    print('  id=%-7s %-9s dt=%-10r dr=%-11s cr=%-11s prod=%-8s q=%-7s pu=%-11s tax_line=%s'
          % (r['id'], r['code'], r['display_type'], r['debit'], r['credit'],
             r['product_id'], r['quantity'], r['price_unit'], r['tax_line_id']))
