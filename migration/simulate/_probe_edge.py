# -*- coding: utf-8 -*-
r"""Probe: วินิจฉัย edge cases ที่ทำให้ replicate ไม่ตรง
  A) od15 tax (sale/purchase) -> ชื่อ + บัญชี repartition
  B) ใบ IS2879 / IS2997: ชื่อ tax และบัญชีของบรรทัดสินค้า
  C) ค่า discount ที่นอกช่วง 0..100 ใน od15
"""
import os
import sys

_ID = os.path.join(os.getcwd(), 'migration', 'import')
if _ID not in sys.path:
    sys.path.insert(0, _ID)
import legacy  # noqa: E402


def _bootstrap_od15_env():
    if os.environ.get('OD15_PASSWORD'):
        return
    conf = os.path.join(os.getcwd(), 'odoo.conf')
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


_bootstrap_od15_env()

print('==== A) od15 taxes (sale/purchase) -> repartition account ====')
rp_cols = legacy.fetch_all(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='account_tax_repartition_line' ORDER BY 1")
print('  repartition cols:', [c['column_name'] for c in rp_cols])
fk = 'invoice_tax_id'
sql_a = (
    "SELECT t.id, t.name, t.type_tax_use, t.amount, a.code AS acc_code "
    "FROM account_tax t "
    "LEFT JOIN account_tax_repartition_line rp "
    "  ON rp.%s=t.id AND rp.repartition_type='tax' "
    "LEFT JOIN account_account a ON a.id=rp.account_id "
    "WHERE t.type_tax_use IN ('sale','purchase') "
    "ORDER BY t.type_tax_use, t.name, a.code") % fk
rows = legacy.fetch_all(sql_a)
for r in rows:
    print('  %(id)s %(type_tax_use)-8s %(amount)-6s %(acc_code)-10s %(name)s' % r)

print('==== B) ใบ IS2879 / IS2997: tax บนบรรทัดสินค้า ====')
for name in ('IS2879', 'IS2997'):
    moves = legacy.fetch_all(
        "SELECT id, name, date FROM account_move WHERE name=%(n)s LIMIT 1", {'n': name})
    if not moves:
        print('  not found:', name)
        continue
    mid = moves[0]['id']
    print('  -- %s (%s) --' % (name, moves[0]['date']))
    lrows = legacy.fetch_all(
        "SELECT a.code AS acc, l.name AS nm, l.debit, l.credit, l.tax_line_id, "
        "       (SELECT string_agg(DISTINCT atx.name, ',') "
        "        FROM account_move_line_account_tax_rel r "
        "        JOIN account_tax atx ON atx.id=r.account_tax_id "
        "        WHERE r.account_move_line_id=l.id) AS taxes, "
        "       (SELECT at2.name FROM account_tax at2 WHERE at2.id=l.tax_line_id) AS taxline_name "
        "FROM account_move_line l JOIN account_account a ON a.id=l.account_id "
        "WHERE l.move_id=%(m)s ORDER BY l.id", {'m': mid})
    for r in lrows:
        print('     %(acc)-9s d=%(debit)s c=%(credit)s taxline=%(taxline_name)s '
              'taxes=%(taxes)s nm=%(nm)s' % r)

print('==== C) discount นอกช่วง 0..100 ใน od15 (ม.ค.-ส.ค. 2026) ====')
rows = legacy.fetch_all(
    "SELECT count(*) AS n FROM account_move_line l "
    "JOIN account_move m ON m.id=l.move_id "
    "WHERE m.date BETWEEN '2026-01-01' AND '2026-08-31' "
    "  AND (l.discount > 100 OR l.discount < 0)")
print('  count =', rows[0]['n'])
rows = legacy.fetch_all(
    "SELECT DISTINCT l.discount FROM account_move_line l "
    "JOIN account_move m ON m.id=l.move_id "
    "WHERE m.date BETWEEN '2026-01-01' AND '2026-08-31' "
    "  AND (l.discount > 100 OR l.discount < 0) ORDER BY l.discount LIMIT 20")
print('  distinct values =', [r['discount'] for r in rows])
rows = legacy.fetch_all(
    "SELECT min(l.discount) AS mn, max(l.discount) AS mx, "
    "       count(*) FILTER (WHERE l.discount IS NOT NULL AND l.display_type IS NULL) AS n "
    "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
    "WHERE m.date BETWEEN '2026-01-01' AND '2026-08-31'")
print('  overall min/max/discount-rows =', rows[0])

print('==== D) บัญชีของบรรทัดภาษี od15 (ต่อ tax) ม.ค.-ส.ค. 2026 ====')
rows = legacy.fetch_all(
    "SELECT t.name AS taxname, a.code AS acc, count(*) AS n, "
    "       round(sum(l.credit-l.debit)::numeric,2) AS net "
    "FROM account_move_line l "
    "JOIN account_move m ON m.id=l.move_id "
    "JOIN account_tax t ON t.id=l.tax_line_id "
    "JOIN account_account a ON a.id=l.account_id "
    "WHERE m.date BETWEEN '2026-01-01' AND '2026-08-31' AND m.state='posted' "
    "GROUP BY 1,2 ORDER BY 1, 3 DESC")
for r in rows:
    print('  %-26s %-10s n=%-6s net=%s' % (r['taxname'], r['acc'], r['n'], r['net']))

print('==== E) ใบที่มีภาษี (บรรทัด tax) มากกว่า 1 ชนิดต่อใบ (ม.ค.-ส.ค. 2026) ====')
for _use, _mts in (('purchase', "'in_invoice','in_refund'"), ('sale', "'out_invoice','out_refund'")):
    rows = legacy.fetch_all(
        "SELECT m.move_type AS mt, count(*) AS n FROM ("
        "  SELECT m.id, m.move_type FROM account_move m "
        "  JOIN account_move_line l ON l.move_id=m.id "
        "  JOIN account_tax t ON t.id=l.tax_line_id "
        "  WHERE m.state='posted' AND m.date BETWEEN '2026-01-01' AND '2026-08-31' "
        "    AND m.move_type IN (" + _mts + ") AND t.type_tax_use='" + _use + "' "
        "  GROUP BY m.id, m.move_type HAVING count(DISTINCT t.id) >= 2"
        ") m GROUP BY 1 ORDER BY 2 DESC")
    print('  [%s] ใบที่มี tax หลายชนิด:' % _use, [(r['mt'], r['n']) for r in rows])
    rows2 = legacy.fetch_all(
        "SELECT combo, count(*) AS n FROM ("
        "  SELECT m.id, string_agg(DISTINCT t.name, ' + ' ORDER BY t.name) AS combo "
        "  FROM account_move m JOIN account_move_line l ON l.move_id=m.id "
        "  JOIN account_tax t ON t.id=l.tax_line_id "
        "  WHERE m.state='posted' AND m.date BETWEEN '2026-01-01' AND '2026-08-31' "
        "    AND m.move_type IN (" + _mts + ") AND t.type_tax_use='" + _use + "' "
        "  GROUP BY m.id HAVING count(DISTINCT t.id) >= 2"
        ") y GROUP BY combo ORDER BY 2 DESC LIMIT 20")
    for r in rows2:
        print('     %-55s n=%s' % (r['combo'], r['n']))
