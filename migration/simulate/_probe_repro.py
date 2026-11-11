# -*- coding: utf-8 -*-
r"""Probe: ทดสอบว่า od19 reproduce บรรทัดของ od15 ได้ตรงแค่ไหน (typed invoice + entry)

- สุ่มใบ od15 ที่ซับซ้อนที่สุด (จำนวนบรรทัดมากสุด) ต่อชนิด
- สร้าง counterpart ใน od19:
    * ใบซื้อ/ขาย -> typed invoice (invoice_line_ids) ให้ Odoo คำนวณภาษี/AR/AP เอง
    * entry (GL)  -> move_type='entry' คัดลอก line_ids 1:1
- เปรียบเทียบ 2 ระดับ: ยอดสุทธิต่อบัญชี (GL) และรายบรรทัด (diagnostic)
- ทุกใบอยู่ใน savepoint แล้ว rollback (ไม่กระทบข้อมูลจริง)

ตัวแปรสภาพแวดล้อม
    REPRO_N=4            จำนวนใบต่อชนิด (ค่าเริ่มต้น 4)
    REPRO_TYPES=...      ชนิดที่ทดสอบ คั่นด้วย , (ค่าเริ่มต้น ทุกชนิด)
"""
import os
import sys
import re

# bootstrap migration/import
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
N_PER_TYPE = int(os.environ.get('REPRO_N', '4'))
TYPES = [t for t in os.environ.get(
    'REPRO_TYPES', 'out_invoice,in_invoice,out_refund,in_refund,entry').split(',') if t]
# REPRO_ORDER=lines (ค่าเริ่มต้น: ใบที่มีบรรทัดมากสุด) หรือ random (สุ่มทั่วทั้งประชากร)
ORDER = os.environ.get('REPRO_ORDER', 'lines').strip() or 'lines'


def account19(code15):
    code19 = AMAP.get(code15)
    if not code19:
        return None, 'no-map:%s' % code15
    acc = env['account.account'].search([('code', '=', code19)], limit=1)
    if not acc:
        return None, 'no-acc:%s' % code19
    return acc, None


def tax19(name15, is_purchase):
    """หา tax ใน od19 — บังคับ type_tax_use ตามชนิดเอกสารก่อนเสมอ

    เหตุผล: od19 มี tax ชื่อ '7%' 2 ตัว (id=1 purchase, id=2 sale)
    ถ้าค้นด้วยชื่ออย่างเดียวจะได้ตัว purchase ก่อน ทำให้ใบขายลงบัญชีผิด (1151.01 แทน 2211.01)
    """
    if not name15:
        return None, None
    use = 'purchase' if is_purchase else 'sale'
    name19 = TMAP.get(name15)
    if name19:
        t = env['account.tax'].search(
            [('name', '=', name19), ('type_tax_use', '=', use)], limit=1)
        if t:
            return t, None
        t = env['account.tax'].search([('name', '=', name19)], limit=1)
        if t:
            return t, None
        return None, 'no-tax:%s' % name19
    m = re.search(r'(\d+(?:\.\d+)?)%', name15 or '')
    if m:
        amount = float(m.group(1))
        t = env['account.tax'].search(
            [('amount', '=', amount), ('type_tax_use', '=', use)], limit=1)
        if t:
            return t, None
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


def pick_samples():
    order = 'n DESC' if ORDER == 'lines' else 'random()'
    samples = []
    for mt in TYPES:
        rows = legacy.fetch_all(
            "SELECT m.id, m.name, m.move_type, m.date, m.ref, m.partner_id, "
            "       m.invoice_date, j.code AS jcode, "
            "       (SELECT count(*) FROM account_move_line l WHERE l.move_id=m.id) AS n "
            "FROM account_move m JOIN account_journal j ON j.id=m.journal_id "
            "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
            "  AND m.move_type=%(mt)s ORDER BY " + order + " LIMIT %(lim)s",
            {'d1': D1, 'd2': D2, 'mt': mt, 'lim': N_PER_TYPE})
        samples.extend(rows)
    return samples


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


def od19_lines_of(move):
    return sorted([(l.account_id.code, round(l.debit, 2), round(l.credit, 2))
                   for l in move.line_ids])


def _agg_by_account(rows):
    """รวมยอดสุทธิ (debit-credit) ต่อรหัสบัญชี — ตัวชี้วัดที่ Trial Balance ใช้"""
    d = {}
    for row in rows:
        c, dr, cr = row[0], row[1], row[2]
        d[c] = round(d.get(c, 0.0) + dr - cr, 2)
    return d


def _compare(rec, move, l15, warns):
    got = od19_lines_of(move)
    exp = sorted([(AMAP.get(r['code'], r['code']), round(float(r['debit'] or 0), 2),
                   round(float(r['credit'] or 0), 2)) for r in l15])
    ga, ea = _agg_by_account(got), _agg_by_account(exp)
    acct_diff = []
    for c in sorted(set(ga) | set(ea)):
        if round(ga.get(c, 0.0) - ea.get(c, 0.0), 2) != 0.0:
            acct_diff.append((c, round(ea.get(c, 0.0), 2), round(ga.get(c, 0.0), 2)))
    gg, ee = list(got), list(exp)
    for item in list(gg):
        if item in ee:
            gg.remove(item)
            ee.remove(item)
    det15 = [{'code': r['code'], 'nm': (r['name'] or '')[:28],
              'q': float(r['quantity'] or 0), 'pu': float(r['price_unit'] or 0),
              'dc': float(r['discount'] or 0), 'dt': r['display_type'],
              'taxline': bool(r['tax_line_id']), 'at': r['atype'],
              'tx': list(r['taxes'] or [])} for r in l15]
    return {'name': rec['name'], 'mt': rec['move_type'], 'n15': len(l15),
            'n19': len(got), 'extra': gg, 'missing': ee,
            'acct_diff': acct_diff, 'warns': sorted(set(warns)), 'det15': det15}


def build_invoice(rec, l15, warns):
    p = partner19(rec['partner_id'])
    if not p:
        return 'no-partner'
    journal = journal19(rec['jcode'])
    if not journal:
        return 'no-journal:%s' % rec['jcode']
    # sync AR/AP property ตามบัญชีที่ od15 ใช้ในใบนี้
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
    tax_used = {}   # od19 tax id -> set(ชื่อ tax od15) สำหรับ override บัญชีบรรทัดภาษี
    for r in l15:
        if r['display_type'] in ('line_section', 'line_note'):
            continue
        if r['tax_line_id']:
            continue  # บรรทัดภาษี
        if r['atype'] in ('receivable', 'payable'):
            continue  # AR/AP เกิดเองจาก partner property
        acc, err = account19(r['code'])
        if not acc:
            warns.append(err)
            return 'skip-line-acc %s' % warns
        tax_ids = []
        for tname in (r['taxes'] or []):
            t, terr = tax19(tname, is_purchase)
            if t:
                tax_ids.append(t.id)
                tax_used.setdefault(t.id, set()).add(tname)
            else:
                warns.append(terr)
        qty = float(r['quantity']) if r['quantity'] is not None else 1.0
        pu = float(r['price_unit'] or 0.0)
        dc = float(r['discount'] or 0.0)
        # ยึด price_subtotal ของ od15: ถ้าสูตรไม่ตรง (discount>100 หรือข้อมูล import เพี้ยน)
        # -> ใช้ qty=1, pu=subtotal, discount=0 ให้ subtotal ตรงเป๊ะ
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
    # override บัญชีบรรทัดภาษี ให้ตรงบัญชีที่ od15 ใช้จริงในใบนี้ (เช่น 2211-02 / 1151-02 / 4300-02)
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
    # ใบซื้อ: OCA l10n_th_account_tax บังคับ tax_invoice_number/date ก่อน post
    # od15 ไม่มีฟิลด์นี้ -> ใช้ ref (เลขใบกำกับผู้ขาย) และ invoice_date แทน
    if is_purchase and move.tax_invoice_ids:
        move.tax_invoice_ids.write({
            'tax_invoice_number': rec['ref'] or rec['name'] or '/',
            'tax_invoice_date': rec['invoice_date'] or rec['date'],
        })
    move.action_post()
    return move


def build_entry(rec, l15, warns):
    journal = journal19(rec['jcode'])
    if not journal:
        return 'no-journal:%s' % rec['jcode']
    lines = []
    for r in l15:
        acc, err = account19(r['code'])
        if not acc:
            warns.append(err)
            return 'skip-line-acc %s' % warns
        vals = {
            'account_id': acc.id,
            'name': (r['name'] or '')[:64] or '/',
            'debit': round(float(r['debit'] or 0), 2),
            'credit': round(float(r['credit'] or 0), 2),
        }
        p = partner19(r['partner_id'])
        if p:
            vals['partner_id'] = p.id
        lines.append((0, 0, vals))
    if not lines:
        return 'no-lines'
    move = env['account.move'].with_context(
        od19_skip_86_4_validation=True).create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': rec['date'],
            'ref': rec['ref'] or False,
            'line_ids': lines,
        })
    move.action_post()
    return move


def build_and_compare(rec):
    l15 = od15_lines(rec['id'])
    if not l15:
        return 'no-od15-lines'
    warns = []
    if rec['move_type'] == 'entry':
        move = build_entry(rec, l15, warns)
    else:
        move = build_invoice(rec, l15, warns)
    if isinstance(move, str):
        return move
    return _compare(rec, move, l15, warns)


def main():
    common.init(env)  # noqa: F821
    _bootstrap_od15_env()
    samples = pick_samples()
    print('==== REPRO TEST: %d ใบ (N/type=%d, order=%s, types=%s) ====' %
          (len(samples), N_PER_TYPE, ORDER, ','.join(TYPES)))
    pop = {}
    for mt in TYPES:
        r = legacy.fetch_one(
            "SELECT count(*) AS c FROM account_move WHERE state='posted' "
            "AND date BETWEEN %(d1)s AND %(d2)s AND move_type=%(mt)s",
            {'d1': D1, 'd2': D2, 'mt': mt})
        pop[mt] = r['c']
    print('   ประชากรทั้งหมด:', pop)
    tot_ok = 0
    diffs = []
    for rec in samples:
        title = '%s %s %s' % (rec['move_type'], rec['name'], rec['date'])
        try:
            with env.cr.savepoint():
                res = build_and_compare(rec)
                if isinstance(res, str):
                    print('  [ERR] %s -> %s' % (title, res))
                elif not res['acct_diff']:
                    tag = 'OK ' if not res['extra'] and not res['missing'] else 'OK~'
                    note = ' (ต่างเฉพาะรายบรรทัด/ยอดสุทธิตรง)' if tag == 'OK~' else ''
                    print('  [%s] %s | lines15=%s lines19=%s%s' %
                          (tag, title, res['n15'], res['n19'], note))
                    tot_ok += 1
                else:
                    print('  [DIF] %s | L15=%s L19=%s' % (title, res['n15'], res['n19']))
                    print('       acct(exp,got): %s' % (res['acct_diff'][:8],))
                    if res['extra']:
                        print('       extra  : %s' % res['extra'][:6])
                    if res['missing']:
                        print('       missing: %s' % res['missing'][:6])
                    if res['warns']:
                        print('       warns  : %s' % res['warns'][:4])
                    diffs.append(res)
                raise RuntimeError('rollback')  # บังคับ rollback
        except RuntimeError as exc:
            if str(exc) != 'rollback':
                print('  [EXC] %s -> %s' % (title, str(exc).splitlines()[0]))
        except Exception as exc:  # noqa: BLE001
            print('  [EXC] %s -> %s' % (title, str(exc).splitlines()[0]))
    print('==== สรุป: ยอดสุทธิบัญชีตรง %d/%d ====' % (tot_ok, len(samples)))


main()
