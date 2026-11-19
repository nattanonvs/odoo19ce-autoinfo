# -*- coding: utf-8 -*-
r"""sim_daily_sales — จำลองข้อมูลขายรายวัน (ม.ค.–ส.ค. 2569) ใน Odoo 19

เป้าหมาย
    ทำให้ Odoo 19 (odoo19_puat) มียอดขายที่ "บันทึกลงบัญชี" (posted) ครบ
    ในช่วง ม.ค.–ส.ค. 2569 โดยอ้างอิงตัวเลขรายได้รายวันจาก Odoo 15 (od15_stage)

หลักการ
    * อ่าน od15_stage อย่างเดียว (legacy.py บังคับ read-only)
    * เขียน odoo19_puat ผ่าน ORM เท่านั้น
    * 1 ใบแจ้งหนี้ (out_invoice) ต่อ 1 วันที่มีรายได้
        - บรรทัดแยกตามบัญชีรายได้ (map รหัส od15 -> od19 ด้วย
          migration/mapping/od15_code_to_od19_code.csv)
        - คิดภาษีขาย VAT 7%
    * ผูก External ID __import15__.<model>.<key> เพื่อรันซ้ำได้ (idempotent)
      และเอกสารที่ post แล้วจะไม่ถูกแก้ไข

วิธีรัน (จาก root โปรเจกต์ c:\odoo-dev\odoo19):
    $env:OD15_PASSWORD = "odoo123"
    Get-Content -LiteralPath .\migration\simulate\sim_daily_sales.py -Raw |
        .\venv19\Scripts\python.exe .\odoo-bin shell -c .\odoo.conf `
        -d odoo19_puat --no-http --db-filter=^odoo19_puat$

ตัวแปรสภาพแวดล้อม
    MIG_DRY_RUN=1        ไม่เขียนข้อมูล (preview เท่านั้น)
    SIM_YEAR=2026        ปีเป้าหมาย (ค่าเริ่มต้น 2026)
    SIM_MONTH_FROM=1     เดือนเริ่มต้น
    SIM_MONTH_TO=8       เดือนสุดท้าย
    SIM_LIMIT=0          จำกัดจำนวนวัน (0 = ทั้งหมด)
    SIM_TAG=simdaily     prefix ของ External ID (กันชนกับผู้ใช้ผู้อื่น)
    SIM_RESET=1          ลบเอกสารจำลองเดิมทั้งหมดก่อนสร้างใหม่ (เริ่มสะอาด)
"""
import os
import sys
import datetime


def _bootstrap_import_dir():
    """หาโฟลเดอร์ migration/import (ใน odoo shell ไม่มี __file__)."""
    cand = os.environ.get('MIG_IMPORT_DIR')
    if cand and os.path.isfile(os.path.join(cand, 'common.py')):
        return os.path.abspath(cand)
    here = os.getcwd()
    for _ in range(6):
        guess = os.path.join(here, 'migration', 'import')
        if os.path.isfile(os.path.join(guess, 'common.py')):
            return guess
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    raise RuntimeError("ไม่พบโฟลเดอร์ migration/import — กำหนด MIG_IMPORT_DIR")


_ID = _bootstrap_import_dir()
if _ID not in sys.path:
    sys.path.insert(0, _ID)

import common  # noqa: E402
import legacy  # noqa: E402


def _bootstrap_od15_env():
    """อ่านค่าการเชื่อมต่อฝั่ง od15 จาก odoo.conf (ห้ามฝัง credential ในคำสั่งรัน)

    ตั้งค่า OD15_HOST/PORT/USER/PASSWORD จาก odoo.conf เฉพาะเมื่อยังไม่มีการตั้ง
    ผ่าน environment variable (ค่าฐานข้อมูลเป้าหมายยังคงเป็น od15_stage ตามค่าเริ่มต้น)
    """
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


# --------------------------------------------------------------------------
# พารามิเตอร์
# --------------------------------------------------------------------------
YEAR = int(os.environ.get('SIM_YEAR', '2026'))
MONTH_FROM = int(os.environ.get('SIM_MONTH_FROM', '1'))
MONTH_TO = int(os.environ.get('SIM_MONTH_TO', '8'))
LIMIT = int(os.environ.get('SIM_LIMIT', '0') or '0')
TAG = os.environ.get('SIM_TAG', 'simdaily')
DUE_DAYS = 30

DATE_FROM = datetime.date(YEAR, MONTH_FROM, 1)
if MONTH_TO >= 12:
    DATE_TO = datetime.date(YEAR + 1, 1, 1)
else:
    DATE_TO = datetime.date(YEAR, MONTH_TO + 1, 1)

MONTH_TH = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
            'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']

# od19 code -> account.account (แคช)
_acct_cache = {}
# od15 code -> od19 code
_amap = None


# --------------------------------------------------------------------------
# การ map รหัสบัญชี od15 -> od19
# --------------------------------------------------------------------------
def load_account_map():
    rows = common.load_map('od15_code_to_od19_code.csv')
    out = {}
    for code15, row in rows.items():
        code19 = (row.get('รหัส Odoo 19') or '').strip()
        if code19:
            out[code15] = code19
    common.log("โหลดการ map รหัสบัญชี %d รายการ" % len(out))
    return out


def get_account(code19):
    if code19 in _acct_cache:
        return _acct_cache[code19]
    env = common.odoo_env()
    acc = env['account.account'].search(
        [('code', '=', code19), ('company_ids', 'in', env.company.id)], limit=1)
    if not acc:
        acc = env['account.account'].search([('code', '=', code19)], limit=1)
    _acct_cache[code19] = acc
    return acc


# --------------------------------------------------------------------------
# ดึงรายได้รายวันจาก Odoo 15
# --------------------------------------------------------------------------
def fetch_daily_revenue():
    sql = (
        "SELECT to_char(m.date, 'YYYY-MM-DD') AS d, a.code AS code, "
        "       sum(l.balance) AS bal, count(*) AS n "
        "FROM account_move_line l "
        "JOIN account_move m ON m.id = l.move_id "
        "JOIN account_account a ON a.id = l.account_id "
        "LEFT JOIN account_account_type t ON t.id = a.user_type_id "
        "WHERE m.state = 'posted' AND t.name IN ('Income', 'Other Income') "
        "  AND m.date >= %s AND m.date < %s "
        "GROUP BY 1, 2 ORDER BY 1, 2")
    rows = legacy.fetch_all(sql, (DATE_FROM, DATE_TO))
    days = {}
    for r in rows:
        days.setdefault(r['d'], []).append(r)
    common.log("od15: พบวันที่มีรายได้ %d วัน (ช่วง %s ถึง %s)"
               % (len(days), DATE_FROM, DATE_TO - datetime.timedelta(days=1)))
    return days


# --------------------------------------------------------------------------
# upsert + post เอกสาร 1 ใบ (invoice หรือ credit note) พร้อมนับสถิติ
# --------------------------------------------------------------------------
def _post_day_move(env, stats, key, ref, move_type, partner, journal,
                   lines, d, d_date):
    vals = {
        'move_type': move_type,
        'partner_id': partner.id,
        'journal_id': journal.id,
        'invoice_date': d,
        'date': d,
        'invoice_date_due': d_date + datetime.timedelta(days=DUE_DAYS),
        'ref': ref,
        'invoice_line_ids': lines,
    }
    # เอกสารที่ post แล้ว: ข้าม (idempotent)
    xmlid = common.get_xmlid('account.move', key)
    existing_id = env['ir.model.data']._xmlid_to_res_id(
        xmlid, raise_if_not_found=False)
    if existing_id:
        rec = env['account.move'].browse(existing_id)
        if rec.state == 'posted':
            stats.skipped += 1
            return
        # มีอยู่แล้วแต่ยังเป็นฉบับร่าง -> เขียนบรรทัดใหม่แล้ว post ต่อ (ไม่ทิ้ง)
        stats.bump('updated')
    else:
        rec, action = common.upsert('account.move', key, vals)
        stats.bump(action)
    if not rec:
        return
    try:
        with env.cr.savepoint():
            if rec.state == 'posted':
                rec.button_draft()
            rec.write({'invoice_line_ids': [(5, 0, 0)] + lines})
            if rec.state == 'draft':
                # ข้ามการตรวจ ม.86/4 สำหรับการนำเข้า/จำลองข้อมูล
                # (โมดูล od19_thai_tax_reports รองรับ context นี้โดยตรง)
                rec.with_context(
                    od19_skip_86_4_validation=True).action_post()
    except Exception as exc:  # noqa: BLE001
        stats.error += 1
        common.log("ล้มเหลว %s (%s): %s" % (d, ref, str(exc).splitlines()[0]))


# --------------------------------------------------------------------------
# ลบเอกสารจำลองเดิมทั้งหมด (ใช้เมื่อเปลี่ยนตรรกะการจำลอง ต้องการเริ่มใหม่ให้สะอาด)
# --------------------------------------------------------------------------
def phase_reset(env):
    common.set_step('sim.reset')
    imd = env['ir.model.data']
    xmlids = imd.search(
        [('module', '=', common.MODULE_PREFIX), ('name', 'like', '%simdaily%')])
    move_ids = [x.res_id for x in xmlids if x.model == 'account.move']
    moves = env['account.move'].browse(move_ids)
    n = len(moves)
    common.log("sim.reset: พบเอกสารจำลองเดิม %d ใบ — กำลังลบ" % n)
    posted = moves.filtered(lambda m: m.state == 'posted')
    if posted:
        posted.button_draft()
    moves.unlink()
    common.log("sim.reset: ลบเอกสารเดิมแล้ว %d ใบ" % n)


# --------------------------------------------------------------------------
# สร้าง/อัปเดตใบแจ้งหนี้รายวัน
# --------------------------------------------------------------------------
def phase_simulate(env):
    common.set_step('sim.invoices')
    if _amap is None:
        raise RuntimeError("ยังไม่ได้โหลดการ map รหัสบัญชี")

    journal = env['account.journal'].search(
        [('type', '=', 'sale'), ('company_id', '=', env.company.id)], limit=1)
    if not journal:
        common.log("ไม่พบสมุดรายวันขาย — หยุด")
        return None, None

    tax = env['account.tax'].search(
        [('type_tax_use', '=', 'sale'), ('amount', '=', 7.0),
         ('company_id', '=', env.company.id)], limit=1)
    if not tax:
        common.log("ไม่พบภาษีขาย 7% — จะบันทึกโดยไม่คิด VAT")

    partners = env['res.partner'].search(
        [('customer_rank', '>', 0),
         ('company_id', 'in', [False, env.company.id])], order='id')
    if not partners:
        common.log("ไม่พบลูกค้า (customer_rank>0) — หยุด")
        return None, None
    common.log("พบสมุดรายวัน %s | ภาษีขาย %s | ลูกค้า %d ราย"
               % (journal.code, tax.name if tax else '-', len(partners)))

    days = fetch_daily_revenue()
    day_keys = sorted(days)
    if LIMIT > 0:
        day_keys = day_keys[:LIMIT]

    stats = common.Stats('sim.invoices')
    missing = {}

    for idx, d in enumerate(day_keys):
        rows = days[d]
        pos_lines, neg_lines = [], []
        for r in sorted(rows, key=lambda x: x['code']):
            amt = -float(r['bal'] or 0.0)     # รายได้เป็นบวก
            if abs(amt) < 0.005:
                continue
            code19 = _amap.get(r['code'])
            if not code19:
                missing[r['code']] = missing.get(r['code'], 0) + 1
                continue
            acc = get_account(code19)
            if not acc:
                missing['%s->%s' % (r['code'], code19)] = \
                    missing.get('%s->%s' % (r['code'], code19), 0) + 1
                continue
            line = (0, 0, {
                'name': '%s' % (acc.display_name or code19),
                'account_id': acc.id,
                'quantity': 1.0,
                'price_unit': round(abs(amt), 2),
                'tax_ids': [(6, 0, tax.ids)] if tax else [(6, 0, [])],
            })
            (pos_lines if amt > 0 else neg_lines).append(line)

        if not pos_lines and not neg_lines:
            stats.skipped += 1
            continue

        partner = partners[idx % len(partners)]
        d_date = datetime.datetime.strptime(d, '%Y-%m-%d').date()
        dkey = d.replace('-', '')
        # บรรทัดที่ยอดเป็นบวก -> ใบแจ้งหนี้
        if pos_lines:
            _post_day_move(env, stats,
                           '%s_%s' % (TAG, dkey), 'SIM-%s' % dkey,
                           'out_invoice', partner, journal,
                           pos_lines, d, d_date)
        # บรรทัดที่ยอดเป็นลบ (ส่วนลด/คืนสินค้า) -> ใบลดหนี้
        if neg_lines:
            _post_day_move(env, stats,
                           '%s_cn_%s' % (TAG, dkey), 'SIMCN-%s' % dkey,
                           'out_refund', partner, journal,
                           neg_lines, d, d_date)

    common.log("sim.invoices: %s" % stats.summary())
    if missing:
        common.log("บัญชีที่ map ไม่ได้/ไม่มีใน OD19: %s" % missing)
    return stats, journal


# --------------------------------------------------------------------------
# ตรวจผล — เทียบรายได้รายเดือน od15 vs od19
# --------------------------------------------------------------------------
def verify(env):
    common.set_step('sim.verify')
    common.log("เปรียบเทียบรายได้รายเดือน (od15 vs od19)")
    bad = 0
    for m in range(MONTH_FROM, MONTH_TO + 1):
        d1 = datetime.date(YEAR, m, 1)
        d2 = datetime.date(YEAR + 1, 1, 1) if m == 12 else datetime.date(YEAR, m + 1, 1)
        r15 = legacy.fetch_one(
            "SELECT COALESCE(sum(l.balance), 0) AS s "
            "FROM account_move_line l JOIN account_move m ON m.id = l.move_id "
            "JOIN account_account a ON a.id = l.account_id "
            "LEFT JOIN account_account_type t ON t.id = a.user_type_id "
            "WHERE m.state = 'posted' AND t.name IN ('Income', 'Other Income') "
            "  AND m.date >= %s AND m.date < %s", (d1, d2))
        s15 = -float(r15['s'] or 0.0)

        lines = env['account.move.line'].search([
            ('parent_state', '=', 'posted'),
            ('date', '>=', d1), ('date', '<', d2),
            ('account_id.account_type', 'in', ['income', 'income_other']),
        ])
        s19 = -sum(lines.mapped('balance'))
        diff = round(s19 - s15, 2)
        flag = '' if abs(diff) < 0.05 else '  <-- ต่าง'
        if abs(diff) >= 0.05:
            bad += 1
        common.log("  %s %d | od15 = %15.2f | od19 = %15.2f | diff = %10.2f%s"
                   % (MONTH_TH[m], YEAR, s15, s19, diff, flag))
    common.log("ตรวจผล: %s" % ('ตรงทั้งหมด' if bad == 0 else 'มี %d เดือนไม่ตรง' % bad))


def main():
    common.init(env)  # noqa: F821
    _bootstrap_od15_env()
    global _amap
    _amap = load_account_map()

    common.log("sim_daily_sales: เริ่ม | %s ถึง %s | DRY_RUN=%s | ติดต่อ %s"
               % (DATE_FROM, DATE_TO - datetime.timedelta(days=1),
                  common.DRY_RUN, env.company.name))  # noqa: F821

    if os.environ.get('SIM_RESET') == '1' and not common.DRY_RUN:
        phase_reset(env)      # noqa: F821
        env.cr.commit()       # noqa: F821

    phase_simulate(env)   # noqa: F821
    if not common.DRY_RUN:
        env.cr.commit()   # noqa: F821
    verify(env)           # noqa: F821
    common.log("sim_daily_sales: เสร็จสิ้น")


main()
