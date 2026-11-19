# -*- coding: utf-8 -*-
# การทดลอง: Odoo 19 เคารพ line_ids ที่เราระบุบัญชีเองหรือไม่ (rollback เท่านั้น ไม่ commit)
partners = env['res.partner'].search([('supplier_rank', '>', 0)])
partner = partners.filtered(
    lambda p: p.property_account_payable_id.code == '2213.08')[:1]
eq = env['account.account'].search([('account_type', '=', 'equity_unaffected')], limit=1)
pay_acc = env['account.account'].search([('code', '=', '2131.01')], limit=1)
jour = env['account.journal'].search([('type', '=', 'purchase')], limit=1)
print('PARTNER', partner.id, partner.display_name,
      'payprop', partner.property_account_payable_id.code)
print('EQ', eq.code, 'PAYACC', pay_acc.code, 'JOUR', jour.code)

print('--- variant A: explicit line_ids ---')
try:
    mv = env['account.move'].create({
        'move_type': 'in_invoice',
        'partner_id': partner.id,
        'journal_id': jour.id,
        'date': '2026-06-01',
        'invoice_date': '2026-06-01',
        'name': 'EXP-A',
        'line_ids': [
            (0, 0, {'account_id': eq.id, 'name': 'counterpart',
                    'debit': 100.0, 'credit': 0.0,
                    'display_type': 'product', 'quantity': 1, 'price_unit': 100.0}),
            (0, 0, {'account_id': pay_acc.id, 'partner_id': partner.id,
                    'name': 'AP', 'debit': 0.0, 'credit': 100.0}),
        ],
    })
    for l in mv.line_ids:
        print('   ', l.account_id.code, l.debit, l.credit, l.display_type,
              'partner=', l.partner_id.id)
    print('   amount_total=', mv.amount_total, 'residual=', mv.amount_residual)
except Exception as e:
    print('   ERROR', type(e).__name__, e)

print('--- variant B: invoice_line_ids only (auto term line) ---')
try:
    mv2 = env['account.move'].create({
        'move_type': 'in_invoice',
        'partner_id': partner.id,
        'journal_id': jour.id,
        'date': '2026-06-01',
        'invoice_date': '2026-06-01',
        'name': 'EXP-B',
        'invoice_line_ids': [
            (0, 0, {'account_id': eq.id, 'name': 'counterpart',
                    'quantity': 1, 'price_unit': 100.0}),
        ],
    })
    for l in mv2.line_ids:
        print('   ', l.account_id.code, l.debit, l.credit, l.display_type,
              'partner=', l.partner_id.id)
    print('   amount_total=', mv2.amount_total)
except Exception as e:
    print('   ERROR', type(e).__name__, e)

env.cr.rollback()
print('ROLLED BACK')
