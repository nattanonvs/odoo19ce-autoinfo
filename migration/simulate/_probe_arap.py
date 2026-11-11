# -*- coding: utf-8 -*-
"""Probe: ตรวจบัญชี AR/AP ที่ od15 ใช้จริง (ม.ค.-ส.ค. 2026) เทียบค่า default ของ od19"""
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), 'migration', 'import'))
import common  # noqa: E402
import legacy  # noqa: E402

D1 = '2026-01-01'
D2 = '2026-08-31'

print('=== od15: AR/AP accounts used in posted moves (Jan-Aug 2026) ===')
rows = legacy.fetch_all(
    "SELECT a.code AS code, t.type AS atype, m.move_type AS mtype, "
    "       count(*) AS n, count(DISTINCT l.partner_id) AS partners "
    "FROM account_move_line l "
    "JOIN account_move m ON m.id = l.move_id "
    "JOIN account_account a ON a.id = l.account_id "
    "JOIN account_account_type t ON t.id = a.user_type_id "
    "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
    "  AND t.type IN ('receivable','payable') "
    "GROUP BY a.code, t.type, m.move_type "
    "ORDER BY t.type, a.code, m.move_type", {'d1': D1, 'd2': D2})
for r in rows:
    print('  %-10s %-11s %-12s lines=%-6s partners=%s'
          % (r['code'], r['atype'], r['mtype'], r['n'], r['partners']))

print()
print('=== od19: partner default receivable/payable (sample + counts) ===')
Partner = env['res.partner']
recv = Partner.read_group([('property_account_receivable_id', '!=', False)],
                          ['id'], ['property_account_receivable_id'])
for g in recv:
    print('  recv', g.get('property_account_receivable_id'), 'count=', g['__count'])
pay = Partner.read_group([('property_account_payable_id', '!=', False)],
                         ['id'], ['property_account_payable_id'])
for g in pay:
    print('  pay ', g.get('property_account_payable_id'), 'count=', g['__count'])

print()
print('=== od19: account 1130.00 / 1130.01 / 2131.00 / 2131.01 ===')
for code in ('1130.00', '1130.01', '1130.02', '2131.00', '2131.01', '2111.00'):
    acc = env['account.account'].search([('code', '=', code)], limit=1)
    if acc:
        print('  %-9s id=%-5s type=%-20s name=%s'
              % (code, acc.id, acc.account_type, acc.name))
    else:
        print('  %-9s NOT FOUND' % code)
