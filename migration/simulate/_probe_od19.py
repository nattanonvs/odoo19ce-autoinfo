# -*- coding: utf-8 -*-
"""Probe od19: partner default AR/AP accounts + opening AR balance by account"""
Partner = env['res.partner']
accs = env['account.account'].search(
    [('account_type', 'in', ('asset_receivable', 'liability_payable'))])
print('=== od19: partner counts by default receivable/payable ===')
for a in accs:
    nr = Partner.search_count([('property_account_receivable_id', '=', a.id)])
    np_ = Partner.search_count([('property_account_payable_id', '=', a.id)])
    if nr or np_:
        print('  %-9s id=%-5s type=%-18s recv_partners=%-5s pay_partners=%s'
              % (a.code, a.id, a.account_type, nr, np_))

print()
print('=== od19: partners with NO default receivable/payable ===')
print('  no recv =', Partner.search_count([('property_account_receivable_id', '=', False)]))
print('  no pay  =', Partner.search_count([('property_account_payable_id', '=', False)]))

print()
print('=== od19: opening AR/AP movement by account (ALL posted moves) ===')
print('  (ก่อน replicate — ควรเป็นเฉพาะยอดยกมา ณ 2026-10-31)')
groups = env['account.move.line']._read_group(
    [('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
     ('parent_state', '=', 'posted')],
    ['account_id'], ['balance:sum'])
for acc, total in groups:
    print('  %-9s %-18s balance=%s' % (acc.code, acc.account_type, total))

print()
print('=== od19: total moves / by type ===')
for mt in ('entry', 'out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
    print('  %-12s %s' % (mt, env['account.move'].search_count([('move_type', '=', mt)])))
print('  TOTAL       ', env['account.move'].search_count([]))
