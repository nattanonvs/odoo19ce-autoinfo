# -*- coding: utf-8 -*-
r"""Dump บรรทัดของ move หนึ่งใบ (od15 เทียบ od19 ที่สร้างขึ้น) — debug
ใช้: MOVE_NAME=APTH2601-0025
"""
import os
import sys

_ID = os.path.join(os.getcwd(), 'migration', 'import')
if _ID not in sys.path:
    sys.path.insert(0, _ID)
import common  # noqa: E402
import legacy  # noqa: E402

sys.path.insert(0, os.path.join(os.getcwd(), 'migration', 'simulate'))

NAME = os.environ.get('MOVE_NAME', 'APTH2601-0025')


def _bootstrap_od15_env():
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

AMAP = {k: (v.get('รหัส Odoo 19') or '').strip()
        for k, v in common.load_map('od15_code_to_od19_code.csv').items()}

import _probe_fix as F  # noqa: E402
F.env = env  # noqa: F821  (inject shell env เข้าโมดูล)
F._bootstrap_od15_env()
common.init(env)  # noqa: F821

print('================ od15 lines: %s ================' % NAME)
mv = legacy.fetch_all("SELECT id, move_type, date, ref, partner_id, journal_id, invoice_date, state "
                      "FROM account_move WHERE name=%(n)s", {'n': NAME})
print('move:', mv)
if not mv:
    raise SystemExit(0)
rec = dict(mv[0])
rec['name'] = NAME
j = legacy.fetch_all("SELECT code FROM account_journal WHERE id=%(i)s", {'i': rec['journal_id']})
rec['jcode'] = j[0]['code']
l15 = F.od15_lines(rec['id'])
for r in l15:
    print('  %-11s d=%-12s c=%-12s q=%-8s pu=%-10s dc=%-9s sub=%-11s dt=%-12s taxline=%s atype=%s tx=%s nm=%s'
          % (r['code'], r['debit'], r['credit'], r['quantity'], r['price_unit'], r['discount'],
             r['price_subtotal'], r['display_type'], r['taxline_name'], r['atype'], list(r['taxes'] or []),
             (r['name'] or '')[:26]))

print('================ od19 lines (build +taxacct+fixdisc) ================')
warns = []
with env.cr.savepoint():  # noqa: F821
    m = F.build(rec, l15, warns, override_tax_acct=True, fix_discount=True)
    print('result:', type(m).__name__ if not isinstance(m, str) else m, 'warns=', sorted(set(warns)))
    if not isinstance(m, str):
        for l in m.line_ids:
            print('  %-11s d=%-12s c=%-12s taxline=%s nm=%s' %
                  (l.account_id.code, l.debit, l.credit, l.tax_line_id.name, (l.name or '')[:26]))
    raise RuntimeError('rollback')
