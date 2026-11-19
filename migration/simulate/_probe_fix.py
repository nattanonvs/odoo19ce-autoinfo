# -*- coding: utf-8 -*-
r"""Probe: ทดสอบวิธีแก้ 2 ปัญหา replicate (typed invoice)

  P1: บรรทัดภาษีลงบัญชีไม่ตรง od15 (เช่น 2211-02 / 1151-02 / 4300-02)
      -> สร้างใบ (draft) แล้ว override account_id ของ tax line ให้ตรงบัญชีที่ od15 ใช้จริง
  P2: discount>100 ชน check constraint ของ od19
      -> แปลงเป็น price_unit = price_subtotal/qty, discount=0

  เปรียบเทียบยอดสุทธิบัญชี (GL) กับ od15 ต่อ 4 สูตร: base / +taxacct / +fixdisc / +both
  ทุกอย่างอยู่ใน savepoint แล้ว rollback (ไม่กระทบข้อมูลจริง)

  ตัวแปร: FIX_K=3 (จำนวนใบต่อกลุ่ม)
"""
import os
import sys
import re

_ID = os.path.join(os.getcwd(), 'migration', 'import')
if _ID not in sys.path:
    sys.path.insert(0, _ID)
import common  # noqa: E402
import legacy  # noqa: E402


def _bootstrap_od15_env():
    if os.environ.get('OD15_PASSWORD'):
        return
    conf = os.path.join(os.getcwd(), 'odoo.conf')
    if not os.path.isfile(conf):
        return
    cfg = {}
    with open(conf, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('[') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            cfg[k.strip()] = v.strip()
    os.environ.setdefault('OD15_HOST', cfg.get('db_host', 'localhost'))
    os.environ.setdefault('OD15_PORT', cfg.get('db_port', '5432'))
    os.environ.setdefault('OD15_USER', cfg.get('db_user', 'odoo'))
    if cfg.get('db_password'):
        os.environ['OD15_PASSWORD'] = cfg['db_password']


AMAP = {k: (v.get('รหัส Odoo 19') or '').strip()
        for k, v in common.load_map('od15_code_to_od19_code.csv').items()}
TMAP = {k: (v.get('od19_tax_name') or '').strip()
        for k, v in common.load_map('tax_map.csv').items()}
D1, D2 = '2026-01-01', '2026-08-31'
K = int(os.environ.get('FIX_K', '3'))


def account19(code15):
    code19 = AMAP.get(code15)
    if not code19:
        return None, 'no-map:%s' % code15
    acc = env['account.account'].search([('code', '=', code19)], limit=1)
    if not acc:
        return None, 'no-acc:%s' % code19
    return acc, None


def tax19(name15, is_purchase):
    if not name15:
        return None, None
    use = 'purchase' if is_purchase else 'sale'
    name19 = TMAP.get(name15)
    if name19:
        t = env['account.tax'].search(
            [('name', '=', name19), ('type_tax_use', '=', use)], limit=1)
        if not t:
            t = env['account.tax'].search([('name', '=', name19)], limit=1)
        if t:
            return t, None
        return None, 'no-tax:%s' % name19
    m = re.search(r'(\d+(?:\.\d+)?)%', name15 or '')
    if m:
        amount = float(m.group(1))
        t = env['account.tax'].search(
            [('amount', '=', amount), ('type_tax_use', '=', use)], limit=1)
        if not t:
            t = env['account.tax'].search([('amount', '=', amount)], limit=1)
        if t:
            return t, None
    return None, 'no-tmap:%s' % name15


def product19(legacy_tmpl_id):
    if not legacy_tmpl_id:
        return None
    xmlid = common.get_xmlid('product.template', legacy_tmpl_id)
    pid = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    if not pid:
        return None
    return env['product.template'].browse(pid).product_variant_id


def partner19(legacy_id):
    if not legacy_id:
        return None
    xmlid = common.get_xmlid('res.partner', legacy_id)
    pid = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    return env['res.partner'].browse(pid) if pid else None


def journal19(code15):
    jm = common.load_map('journal_map.csv').get(code15)
    code19 = (jm.get('od19_journal_code') or code15).strip() if jm else code15
    return env['account.journal'].search(
        [('code', '=', code19), ('company_id', '=', env.company.id)], limit=1)


def od15_lines(move_id):
    return legacy.fetch_all(
        "SELECT l.id, a.code AS code, l.partner_id, l.name, l.debit, l.credit, "
        "       l.quantity, l.price_unit, l.discount, l.price_subtotal, l.product_id, "
        "       t.product_tmpl_id AS tmpl_id, l.display_type, l.tax_line_id, "
        "       (SELECT name FROM account_tax WHERE id=l.tax_line_id) AS taxline_name, "
        "       at.type AS atype, "
        "       (SELECT array_agg(DISTINCT atx.name) FROM account_move_line_account_tax_rel r "
        "        JOIN account_tax atx ON atx.id=r.account_tax_id WHERE r.account_move_line_id=l.id) AS taxes "
        "FROM account_move_line l "
        "JOIN account_account a ON a.id=l.account_id "
        "LEFT JOIN account_account_type at ON at.id=a.user_type_id "
        "LEFT JOIN product_product t ON t.id=l.product_id "
        "WHERE l.move_id=%(mid)s ORDER BY l.id", {'mid': move_id})


def pick(kind):
    base = ("SELECT DISTINCT m.id, m.name, m.move_type, m.date, m.ref, m.partner_id, "
            "       m.invoice_date, j.code AS jcode "
            "FROM account_move m "
            "JOIN account_move_line l ON l.move_id=m.id "
            "JOIN account_journal j ON j.id=m.journal_id ")
    if kind == 'bad_tax':
        sql = (base +
               "JOIN account_tax t ON t.id=l.tax_line_id "
               "JOIN account_account a ON a.id=l.account_id "
               "LEFT JOIN account_tax_repartition_line rp "
               "  ON rp.invoice_tax_id=t.id AND rp.repartition_type='tax' "
               "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
               "  AND m.move_type IN ('out_invoice','in_invoice','out_refund','in_refund') "
               "  AND rp.account_id IS NOT NULL AND a.id <> rp.account_id "
               "ORDER BY m.date LIMIT %(k)s")
    else:
        sql = (base +
               "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
               "  AND l.discount > 100 AND l.display_type IS NULL "
               "ORDER BY m.date LIMIT %(k)s")
    return legacy.fetch_all(sql, {'d1': D1, 'd2': D2, 'k': K})


def build(rec, l15, warns, override_tax_acct=False, fix_discount=False):
    p = partner19(rec['partner_id'])
    if not p:
        return 'no-partner'
    journal = journal19(rec['jcode'])
    if not journal:
        return 'no-journal:%s' % rec['jcode']
    for atype, field in (('receivable', 'property_account_receivable_id'),
                         ('payable', 'property_account_payable_id')):
        codes = [r['code'] for r in l15 if r['atype'] == atype]
        if codes:
            acc, err = account19(codes[0])
            if acc:
                p.with_company(env.company)[field] = acc
            else:
                warns.append(err)

    is_purchase = rec['move_type'] in ('in_invoice', 'in_refund')
    inv_lines = []
    tax_used = {}   # od19 tax id -> set(ชื่อ tax od15)
    for r in l15:
        if r['display_type'] in ('line_section', 'line_note'):
            continue
        if r['tax_line_id']:
            continue
        if r['atype'] in ('receivable', 'payable'):
            continue
        acc, err = account19(r['code'])
        if not acc:
            warns.append(err)
            return 'skip-line-acc:%s' % err
        tax_ids = []
        for tname in (r['taxes'] or []):
            t, terr = tax19(tname, is_purchase)
            if t:
                tax_ids.append(t.id)
                tax_used.setdefault(t.id, set()).add(tname)
            elif terr:
                warns.append(terr)
        qty = float(r['quantity']) if r['quantity'] is not None else 1.0
        pu = float(r['price_unit'] or 0.0)
        dc = float(r['discount'] or 0.0)
        if fix_discount:
            # ยึด price_subtotal ของ od15 เป็นหลัก: ถ้าสูตร (qty*pu*(1-dc/100)) ให้ค่าไม่ตรง
            # (เช่น discount>100 หรือ discount=100 แต่ subtotal>0 จากข้อมูล import)
            # -> ใช้ qty=1, pu=subtotal, discount=0 เพื่อให้ subtotal ตรงเป๊ะ
            sub = round(float(r['price_subtotal'] or 0.0), 2)
            recomputed = round(qty * pu * (1 - dc / 100.0), 2) if 0 <= dc <= 100 else None
            if recomputed != sub:
                qty, pu, dc = 1.0, sub, 0.0
        vals = {
            'account_id': acc.id,
            'name': (r['name'] or '')[:64] or '/',
            'quantity': qty,
            'price_unit': pu,
            'discount': dc,
            'tax_ids': [(6, 0, tax_ids)],
        }
        prod = product19(r['tmpl_id'])
        if prod:
            vals['product_id'] = prod.id
        inv_lines.append((0, 0, vals))
    if not inv_lines:
        return 'no-invoice-lines'
    hd = {
        'move_type': rec['move_type'],
        'partner_id': p.id,
        'journal_id': journal.id,
        'date': rec['date'],
        'invoice_date': rec['invoice_date'] or rec['date'],
        'ref': rec['ref'] or False,
        'invoice_line_ids': inv_lines,
    }
    move = env['account.move'].with_context(
        od19_skip_86_4_validation=True).create(hd)
    if override_tax_acct:
        d15 = {}
        for r in l15:
            if r['tax_line_id'] and r['taxline_name']:
                d15.setdefault(r['taxline_name'], set()).add(r['code'])
        for line in move.line_ids.filtered('tax_line_id'):
            names15 = tax_used.get(line.tax_line_id.id)
            if not names15:
                continue
            codes = set()
            for n in names15:
                codes |= d15.get(n, set())
            if len(codes) == 1:
                acc2, err2 = account19(next(iter(codes)))
                if acc2:
                    line.account_id = acc2.id
                else:
                    warns.append(err2)
            else:
                warns.append('ambig-tax-acct:%s' % sorted(codes))
    if is_purchase and move.tax_invoice_ids:
        move.tax_invoice_ids.write({
            'tax_invoice_number': rec['ref'] or rec['name'] or '/',
            'tax_invoice_date': rec['invoice_date'] or rec['date'],
        })
    move.action_post()
    return move


def agg(rows):
    d = {}
    for c, dr, cr in rows:
        d[c] = round(d.get(c, 0.0) + dr - cr, 2)
    return d


def run(rec, override_tax_acct, fix_discount):
    l15 = od15_lines(rec['id'])
    warns = []
    move = build(rec, l15, warns, override_tax_acct, fix_discount)
    if isinstance(move, str):
        return 'ERR ' + move
    exp = agg([(AMAP.get(r['code'], r['code']), round(float(r['debit'] or 0), 2),
                round(float(r['credit'] or 0), 2)) for r in l15])
    got = agg([(l.account_id.code, round(l.debit, 2), round(l.credit, 2)) for l in move.line_ids])
    diff = [(c, round(exp.get(c, 0.0), 2), round(got.get(c, 0.0), 2))
            for c in sorted(set(exp) | set(got))
            if round(exp.get(c, 0.0) - got.get(c, 0.0), 2) != 0.0]
    return diff, warns


def line_consistency():
    """นับบรรทัดสินค้าที่สูตร (qty*pu*(1-dc/100)) ไม่ตรง price_subtotal ของ od15"""
    rows = legacy.fetch_all(
        "SELECT count(*) AS tot, "
        "  count(*) FILTER (WHERE round(l.quantity*l.price_unit*(1-coalesce(l.discount,0)/100.0),2) "
        "                         <> round(l.price_subtotal,2)) AS bad, "
        "  count(*) FILTER (WHERE l.discount = 100) AS dc100 "
        "FROM account_move_line l "
        "JOIN account_move m ON m.id=l.move_id "
        "JOIN account_account a ON a.id=l.account_id "
        "JOIN account_account_type at ON at.id=a.user_type_id "
        "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
        "  AND m.move_type IN ('out_invoice','in_invoice','out_refund','in_refund') "
        "  AND l.tax_line_id IS NULL AND l.display_type IS NULL "
        "  AND at.type NOT IN ('receivable','payable')", {'d1': D1, 'd2': D2})
    return rows[0]


def main():
    common.init(env)  # noqa: F821
    _bootstrap_od15_env()
    print('==== ความสอดคล้องของบรรทัดสินค้า od15 (qty*pu*(1-dc/100) vs price_subtotal) ====')
    print('  ', line_consistency())
    for kind in ('bad_tax', 'discount'):
        recs = pick(kind)
        print('==== kind=%s -> %d ใบ ====' % (kind, len(recs)))
        for rec in recs:
            title = '%s %s %s' % (rec['move_type'], rec['name'], rec['date'])
            for lbl, ov, fx in (('base', False, False), ('+taxacct', True, False),
                                ('+fixdisc', False, True), ('+both', True, True)):
                try:
                    with env.cr.savepoint():
                        res = run(rec, ov, fx)
                        if isinstance(res, str):
                            print('  [%s] %s -> %s' % (lbl, title, res))
                        else:
                            diff, warns = res
                            if not diff:
                                print('  [%s] %s -> OK (GL ตรง)' % (lbl, title))
                            else:
                                print('  [%s] %s -> DIF %s' % (lbl, title, diff[:6]))
                            if warns:
                                print('        warns: %s' % sorted(set(warns))[:3])
                        raise RuntimeError('rollback')
                except RuntimeError as exc:
                    if str(exc) != 'rollback':
                        print('  [%s] %s EXC %s' % (lbl, title, str(exc).splitlines()[0]))
                except Exception as exc:  # noqa: BLE001
                    print('  [%s] %s EXC %s' % (lbl, title, str(exc).splitlines()[0]))


if __name__ == '__main__':
    main()
