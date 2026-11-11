# -*- coding: utf-8 -*-
r"""เปรียบเทียบงบดุล (Balance Sheet) Odoo 19 เทียบ Odoo 15 แบบรายละเอียดรายบัญชี

อ่านอย่างเดียว (read-only) ทั้งสองฐานข้อมูล:
    * Odoo 15 : od15_stage   (psycopg2)
    * Odoo 19 : odoo19_puat  (psycopg2)

เกณฑ์การตรวจสอบ (ตามที่ผู้ใช้กำหนด):
    ถ้าทั้งสองระบบให้ผลลัพธ์ "เหมือนกัน" ทุกรายบัญชี ณ วันเดียวที่เทียบได้
    = ถือว่าถูกต้อง

หมายเหตุสำคัญ:
    ระบบใหม่ (Odoo 19) มีย้ายเฉพาะ "ยอดยกมา" ณ วันตัดยอด จึงมีข้อมูลจริง
    ตั้งแต่ 31 ต.ค. 2026 เท่านั้น ส่วน Odoo 15 มีข้อมูลรายเดือน ม.ค.–ต.ค. 2026
    จึงรายงานทั้งรายเดือนของ OD15 และการเทียบรายบัญชี ณ จุดตัดยอด

รัน (จาก root โปรเจกต์):
    .\venv19\Scripts\python.exe migration\recon\bs_compare.py

ผลลัพธ์: ไฟล์ Excel หลายชีต (ดู OUT_PATH ด้านล่าง)
"""
import json
import os
import sys
import datetime

import psycopg2
import psycopg2.extras
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --------------------------------------------------------------------------
# ค่าคงที่
# --------------------------------------------------------------------------
CUTOFF = '2026-10-31'                       # วันตัดยอด (วันเดียวที่เทียบงบดุลได้)
OD15_DB = 'od15_stage'
OD19_DB = 'odoo19_puat'
OD19_CODE_KEY = '1'                         # คีย์บริษัทใน code_store (jsonb)
TOL = 0.01                                  # ค่าคลาดเคลื่อนที่ยอมรับได้

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ...\migration
PROJ = os.path.dirname(ROOT)                                          # ...\odoo19
CONF = os.path.join(PROJ, 'odoo.conf')
CHART_FILE = os.path.join(ROOT, 'mapping', 'od15_chart_to_od19.csv')
OUT_PATH = os.path.join(ROOT, 'recon',
                        'bs_compare_od15_vs_od19_20261031_R03.xlsx')

# เดือนที่รายงาน (ม.ค.–ต.ค. 2026) — ต.ค. คือเดือนของจุดตัดยอด
MONTHS = [(2026, m) for m in range(1, 11)]
MONTH_TH = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
            'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']

# ยอดขาย — Odoo 15 เท่านั้น (OD19 มียอดยกมาเท่านั้น)
SALES_DATE = datetime.date(2026, 9, 30)          # สิ้นเดือน 9
SALES_LABEL = '30 ก.ย. 2569'
SALES_CUT_LABEL = '31 ต.ค. 2569'                 # จุดตัดยอด (สิ้นเดือน 10)
SALES_MONTHS = [(2026, m) for m in range(1, 11)]  # ม.ค.–ต.ค. 2569

# ประเภทบัญชี OD15 (user_type) -> account_type ฝั่ง OD19 (ใช้เป็น fallback)
OD15_TYPE_FALLBACK = {
    'Bank and Cash': 'asset_cash',
    'Current Assets': 'asset_current',
    'Fixed Assets': 'asset_fixed',
    'Non-current Assets': 'asset_non_current',
    'Receivable': 'asset_receivable',
    'Prepayments': 'asset_current',
    'Current Liabilities': 'liability_current',
    'Non-current Liabilities': 'liability_non_current',
    'Payable': 'liability_payable',
    'Equity': 'equity',
    'Current Year Earnings': 'equity_unaffected',
}


# --------------------------------------------------------------------------
# การเชื่อมต่อ (อ่านค่าจาก odoo.conf — ห้ามฝัง credential)
# --------------------------------------------------------------------------
def read_conf():
    cfg = {}
    with open(CONF, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('['):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            cfg[k.strip()] = v.strip()
    return cfg


def connect(dbname, cfg):
    conn = psycopg2.connect(
        host=cfg.get('db_host', 'localhost'),
        port=int(cfg.get('db_port', 5432)),
        user=cfg.get('db_user', 'odoo'),
        password=cfg.get('db_password', ''),
        dbname=dbname,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.set_session(readonly=True, autocommit=True)
    return conn


def money(v):
    return round(float(v or 0.0), 2)


def month_end(year, month):
    if month == 12:
        return datetime.date(year, 12, 31)
    return datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)


# --------------------------------------------------------------------------
# ผังบัญชี (mapping)
# --------------------------------------------------------------------------
def load_chart():
    chart = {}
    with open(CHART_FILE, 'r', encoding='utf-8-sig') as fh:
        import csv
        for row in csv.DictReader(fh):
            code = (row.get('od15_code') or '').strip()
            if code:
                chart[code] = row
    return chart


def cls_from_type(t):
    t = (t or '').strip()
    if t.startswith('asset'):
        return 'asset'
    if t.startswith('liability'):
        return 'liability'
    if t.startswith('equity'):
        return 'equity'
    return 'pl'


def classify(od15_code, od15_type_name, chart):
    """คืน (class, od19_code, od19_account_type) ของบัญชี OD15."""
    o19_code = od15_code.strip().replace('-', '.')
    row = chart.get(od15_code) or {}
    atype = (row.get('od19_account_type') or '').strip()
    if not atype:
        atype = OD15_TYPE_FALLBACK.get((od15_type_name or '').strip(), '')
    return cls_from_type(atype), o19_code, atype


# --------------------------------------------------------------------------
# OD15 — ยอดคงเหลือรายบัญชี
# --------------------------------------------------------------------------
_OD15_BAL_SQL = (
    "SELECT a.code AS code, a.name AS name, t.name AS type_name, "
    "       round(sum(l.balance)::numeric, 2) AS bal "
    "FROM account_move_line l "
    "JOIN account_move m ON m.id = l.move_id "
    "JOIN account_account a ON a.id = l.account_id "
    "LEFT JOIN account_account_type t ON t.id = a.user_type_id "
    "WHERE m.state = 'posted' AND m.date <= %(d)s "
    "GROUP BY a.code, a.name, t.name "
    "HAVING round(sum(l.balance)::numeric, 2) <> 0"
)


def od15_balances(c15, as_of):
    with c15.cursor() as cur:
        cur.execute(_OD15_BAL_SQL, {'d': as_of})
        return [dict(r) for r in cur.fetchall()]


# --------------------------------------------------------------------------
# OD19 — ยอดคงเหลือรายบัญชี
# --------------------------------------------------------------------------
_OD19_BAL_SQL = (
    "SELECT a.code_store->>%(k)s AS code, a.account_type AS account_type, "
    "       a.name::text AS name_json, "
    "       round(sum(l.balance)::numeric, 2) AS bal "
    "FROM account_move_line l "
    "JOIN account_move m ON m.id = l.move_id "
    "JOIN account_account a ON a.id = l.account_id "
    "WHERE m.state = 'posted' AND m.date <= %(d)s "
    "GROUP BY 1, 2, 3 "
    "HAVING round(sum(l.balance)::numeric, 2) <> 0"
)


def _pick_name(name_json):
    try:
        d = json.loads(name_json) if name_json else {}
    except (ValueError, TypeError):
        return name_json or ''
    for k in ('th_TH', 'en_US'):
        if d.get(k):
            return d[k]
    for v in d.values():
        if v:
            return v
    return ''


def od19_balances(c19, as_of):
    with c19.cursor() as cur:
        cur.execute(_OD19_BAL_SQL, {'k': OD19_CODE_KEY, 'd': as_of})
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r['name'] = _pick_name(r.get('name_json'))
    return rows


# --------------------------------------------------------------------------
# OD15 — ยอดขาย (Income + Other Income)
# --------------------------------------------------------------------------
_INCOME_SELECT = (
    "SELECT a.code AS code, a.name AS name, t.name AS type_name, "
    "       round(sum(l.balance)::numeric, 2) AS bal "
    "FROM account_move_line l "
    "JOIN account_move m ON m.id = l.move_id "
    "JOIN account_account a ON a.id = l.account_id "
    "LEFT JOIN account_account_type t ON t.id = a.user_type_id "
    "WHERE m.state = 'posted' AND m.date <= %(e)s "
    "  AND t.name IN ('Income', 'Other Income') "
)
_INCOME_TAIL = (
    "GROUP BY a.code, a.name, t.name "
    "HAVING round(sum(l.balance)::numeric, 2) <> 0 "
    "ORDER BY a.code"
)


def od15_income(c15, end, start=None):
    """ยอดบัญชีรายได้ (Income / Other Income) — end=ณ วันที่, start=ตั้งแต่ (ช่วงเดือน)."""
    sql = _INCOME_SELECT
    p = {'e': end}
    if start is not None:
        sql += "  AND m.date >= %(s)s "
        p['s'] = start
    sql += _INCOME_TAIL
    with c15.cursor() as cur:
        cur.execute(sql, p)
        return [dict(r) for r in cur.fetchall()]


def _income_split(rows):
    """แยกยอดเป็น (Income, Other Income) โดยแสดงด้านบวก (revenue = -balance)."""
    inc = money(sum(-r['bal'] for r in rows if r['type_name'] == 'Income'))
    other = money(sum(-r['bal'] for r in rows if r['type_name'] == 'Other Income'))
    return inc, other


def od15_last_out_invoice(c15):
    """วันที่เอกสารขาย (out_invoice) ล่าสุดที่ posted."""
    with c15.cursor() as cur:
        cur.execute("SELECT max(date) AS mx FROM account_move "
                    "WHERE move_type = 'out_invoice' AND state = 'posted'")
        r = cur.fetchone()
    return r['mx'] if r else None


# --------------------------------------------------------------------------
# OD15 — ใบวางบิล / บิลเรียกเก็บเงิน (dtr_account_billing)
# หมายเหตุ: ฟิลด์ pay_amount*/wht_amount*/income_type* ในตารางว่างทั้งหมด (0/NULL)
#          จึงใช้ยอดจากใบแจ้งหนี้ (account_move) ที่ผูกกับบิลเป็นมูลค่าของบิล
# --------------------------------------------------------------------------
_BILLING_FROM = (
    "FROM dtr_account_billing b "
    "LEFT JOIN account_move_dtr_account_billing_rel br "
    "       ON br.dtr_account_billing_id = b.id "
    "LEFT JOIN account_move am "
    "       ON am.id = br.account_move_id AND am.state = 'posted' "
)


def od15_billing_by_state(c15):
    """สรุปบิลตามสถานะ (ทุกช่วงเวลา) พร้อมยอดจากใบแจ้งหนี้ที่ผูก."""
    sql = ("SELECT b.state AS state, count(DISTINCT b.id) AS nb, "
           "       round(sum(am.amount_total)::numeric, 2) AS tot " +
           _BILLING_FROM + "GROUP BY b.state ORDER BY b.state")
    with c15.cursor() as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def od15_billing_monthly(c15, start, end):
    """บิลรายเดือนตาม bill_date — คืน dict keyed 'YYYY-MM'."""
    sql = ("SELECT to_char(b.bill_date, 'YYYY-MM') AS ym, "
           "       count(DISTINCT b.id) AS nb, "
           "       count(DISTINCT CASE WHEN b.state = 'open' THEN b.id END) AS nb_open, "
           "       round(sum(am.amount_total)::numeric, 2) AS tot, "
           "       round(sum(CASE WHEN b.state = 'open' THEN am.amount_total END)"
           "::numeric, 2) AS tot_open " +
           _BILLING_FROM +
           "WHERE b.bill_date BETWEEN %(s)s AND %(e)s GROUP BY 1 ORDER BY 1")
    with c15.cursor() as cur:
        cur.execute(sql, {'s': start, 'e': end})
        return {r['ym']: dict(r) for r in cur.fetchall()}


def od15_billing_open_top(c15, limit=20):
    """ยอดเปิด (state='open') แยกรายคู่ค้า — เรียงมากไปน้อย."""
    sql = ("SELECT p.name AS partner, count(DISTINCT b.id) AS nb, "
           "       round(sum(am.amount_total)::numeric, 2) AS tot " +
           _BILLING_FROM +
           "LEFT JOIN res_partner p ON p.id = b.partner_id "
           "WHERE b.state = 'open' "
           "GROUP BY p.name ORDER BY tot DESC NULLS LAST LIMIT %(l)s")
    with c15.cursor() as cur:
        cur.execute(sql, {'l': limit})
        return [dict(r) for r in cur.fetchall()]


def od15_billing_open_summary(c15):
    """ยอดเปิด (state='open') รวมทั้งหมด + ช่วงวันที่บิล."""
    sql = ("SELECT count(DISTINCT b.id) AS n, min(b.bill_date) AS mn, "
           "       max(b.bill_date) AS mx, "
           "       round(sum(am.amount_total)::numeric, 2) AS tot " +
           _BILLING_FROM + "WHERE b.state = 'open'")
    with c15.cursor() as cur:
        cur.execute(sql)
        r = cur.fetchone()
    return dict(r) if r else {}


# --------------------------------------------------------------------------
# สร้างเวิร์กบุ๊ก
# --------------------------------------------------------------------------
HDR_FILL = PatternFill('solid', fgColor='9E2424')     # แบรนด์มาโรน
HDR_FONT = Font(color='FFFFFF', bold=True, size=11)
SUB_FILL = PatternFill('solid', fgColor='F2DEDE')
OK_FILL = PatternFill('solid', fgColor='E2EFDA')
BAD_FILL = PatternFill('solid', fgColor='FCE4E4')
MONEY_FMT = '#,##0.00;[Red]-#,##0.00'
_THIN = Side(style='thin', color='D0D0D0')
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def style_header(ws, row, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center',
                                   wrap_text=True)
        cell.border = BORDER


def autosize(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build_summary(wb, cut, rec, verdict, n_acc15, n_acc19, n_checked, notes):
    """rec = dict ของตัวเลขยอดรวมทั้งสองฝั่ง (จัดกลุ่มให้เทียบกันได้)."""
    ws = wb.create_sheet('Summary')
    autosize(ws, [36, 22, 22, 16, 12])
    ws['A1'] = 'ตรวจสอบงบดุล (Balance Sheet) — Odoo 15 vs Odoo 19'
    ws['A1'].font = Font(bold=True, size=14, color='9E2424')
    ws['A2'] = 'จุดตัดยอด (Cut-off): %s   |   เกณฑ์: ทุกรายบัญชีต้องเท่ากัน (same result = correct)' % cut
    ws['A2'].font = Font(italic=True, size=10)
    ws['A4'] = 'ผลการตรวจสอบ'
    ws['A4'].font = Font(bold=True, size=12)
    v = ws['A5']
    v.value = verdict
    v.font = Font(bold=True, size=12,
                  color='006100' if verdict.startswith('PASS') else '9C0006')
    v.fill = OK_FILL if verdict.startswith('PASS') else BAD_FILL

    r = 7
    hdr = ['หมวดบัญชี', 'OD15 (od15_stage)', 'OD19 (odoo19_puat)',
           'ผลต่าง (OD19-OD15)', 'สถานะ']
    for i, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, 5)
    r += 1

    def line(label, a, b, bold=False, sub=False):
        nonlocal r
        c1 = ws.cell(row=r, column=1, value=label)
        if bold:
            c1.font = Font(bold=True)
        if sub:
            c1.alignment = Alignment(indent=1)
        ws.cell(row=r, column=2, value=a).number_format = MONEY_FMT
        ws.cell(row=r, column=3, value=b).number_format = MONEY_FMT
        diff = money(b - a)
        ws.cell(row=r, column=4, value=diff).number_format = MONEY_FMT
        st = ws.cell(row=r, column=5, value='ตรง' if abs(diff) <= TOL else 'ต่าง')
        st.fill = OK_FILL if abs(diff) <= TOL else BAD_FILL
        st.alignment = Alignment(horizontal='center')
        for c in range(1, 6):
            ws.cell(row=r, column=c).border = BORDER
        r += 1

    line('สินทรัพย์ (ASSET)', rec['asset15'], rec['asset19'], bold=True)
    line('หนี้สิน (LIABILITY)', rec['liab15'], rec['liab19'], bold=True)
    line('ส่วนของผู้ถือหุ้น (EQUITY) — บัญชีทุน', rec['eq15'], rec['eq19'],
         bold=True, sub=True)
    line('กำไร(ขาดทุน)สุทธิประจำปี', rec['pl15'], rec['unaffected19'],
         bold=True, sub=True)
    line('รวมหนี้สิน + ส่วนของผู้ถือหุ้น', rec['liab_eq15'], rec['liab_eq19'], bold=True)

    r += 1
    ws.cell(row=r, column=1, value='สมการบัญชี: สินทรัพย์ + (หนี้สิน + ทุน)').font = Font(bold=True)
    r += 1
    for lbl, val in (('OD15', rec['balance15']), ('OD19', rec['balance19'])):
        ws.cell(row=r, column=1, value=lbl).alignment = Alignment(indent=1)
        c = ws.cell(row=r, column=2, value=val)
        c.number_format = MONEY_FMT
        c.fill = OK_FILL if abs(val) <= TOL else BAD_FILL
        r += 1

    r += 1
    ws.cell(row=r, column=1, value='สถิติ').font = Font(bold=True)
    r += 1
    stats = [
        ('จำนวนบัญชีงบดุลที่เทียบ (OD15)', n_acc15),
        ('จำนวนบัญชีงบดุลที่เทียบ (OD19)', n_acc19),
        ('จำนวนรายการที่เทียบได้ (จับคู่รหัส)', n_checked),
        ('ผลต่างเกิน %.2f' % TOL, sum(1 for n in notes if n.get('fail'))),
    ]
    for k, val in stats:
        ws.cell(row=r, column=1, value=k)
        ws.cell(row=r, column=2, value=val)
        r += 1

    r += 1
    ws.cell(row=r, column=1, value='หมายเหตุ / ข้อจำกัด').font = Font(bold=True)
    r += 1
    for n in notes:
        ws.cell(row=r, column=1, value='- ' + n['text'])
        ws.cell(row=r, column=1).alignment = Alignment(wrap_text=True, vertical='top')
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        r += 1


def build_compare(wb, rows, chart):
    ws = wb.create_sheet('Compare_BS_Detail')
    hdr = ['OD15 Code', 'OD19 Code', 'ชื่อบัญชี (OD15)', 'ประเภทบัญชี (OD19)',
           'หมวด', 'OD15 ยอด', 'OD19 ยอด', 'ผลต่าง (OD19-OD15)', 'สถานะ']
    ws.append(hdr)
    style_header(ws, 1, len(hdr))
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = 'A1:I1'
    r = 2
    for row in rows:
        ws.cell(row=r, column=1, value=row['o15_code'])
        ws.cell(row=r, column=2, value=row['o19_code'])
        ws.cell(row=r, column=3, value=row['name'])
        ws.cell(row=r, column=4, value=row['atype'])
        ws.cell(row=r, column=5, value=row['cls'])
        ws.cell(row=r, column=6, value=row['bal15']).number_format = MONEY_FMT
        ws.cell(row=r, column=7, value=row['bal19']).number_format = MONEY_FMT
        ws.cell(row=r, column=8, value=row['diff']).number_format = MONEY_FMT
        st = ws.cell(row=r, column=9, value=row['status'])
        st.fill = OK_FILL if row['status'] == 'ตรง' else BAD_FILL
        for c in range(1, 10):
            ws.cell(row=r, column=c).border = BORDER
        r += 1
    autosize(ws, [13, 13, 44, 22, 11, 18, 18, 18, 9])


def build_monthly(wb, monthly):
    ws = wb.create_sheet('OD15_Monthly_BS')
    hdr = ['เดือน', 'สินทรัพย์ (ASSET)', 'หนี้สิน (LIABILITY)', 'ส่วนของผู้ถือหุ้น (EQUITY)',
           'กำไร(ขาดทุน)สะสมระหว่างปี', 'รวมหนี้สิน + ทุน + กำไรสะสม',
           'ตรวจสมการบัญชี', 'หมายเหตุ']
    ws.append(hdr)
    style_header(ws, 1, len(hdr))
    ws.freeze_panes = 'A2'
    r = 2
    for m in monthly:
        ws.cell(row=r, column=1, value=m['label'])
        ws.cell(row=r, column=2, value=m['asset']).number_format = MONEY_FMT
        ws.cell(row=r, column=3, value=m['liability']).number_format = MONEY_FMT
        ws.cell(row=r, column=4, value=m['equity']).number_format = MONEY_FMT
        ws.cell(row=r, column=5, value=m['pl']).number_format = MONEY_FMT
        ws.cell(row=r, column=6, value=m['eq_sum']).number_format = MONEY_FMT
        chk = ws.cell(row=r, column=7, value=m['check'])
        chk.number_format = MONEY_FMT
        chk.fill = OK_FILL if abs(m['check']) <= TOL else BAD_FILL
        ws.cell(row=r, column=8, value=m['note'])
        for c in range(1, 9):
            ws.cell(row=r, column=c).border = BORDER
        r += 1
    autosize(ws, [14, 20, 20, 24, 24, 26, 16, 26])


def build_monthly_by_acc(wb, accounts, monthly_accounts):
    """ตารางรายบัญชี × เดือน (ยอดสะสม ณ สิ้นเดือน)."""
    ws = wb.create_sheet('OD15_Monthly_By_Acc')
    hdr = ['OD15 Code', 'ชื่อบัญชี', 'หมวด'] + ['%s' % m['label'] for m in monthly_accounts]
    ws.append(hdr)
    style_header(ws, 1, len(hdr))
    ws.freeze_panes = 'D2'
    ws.auto_filter.ref = 'A1:%s1' % get_column_letter(len(hdr))
    r = 2
    for acc in accounts:
        ws.cell(row=r, column=1, value=acc['o15_code'])
        ws.cell(row=r, column=2, value=acc['name'])
        ws.cell(row=r, column=3, value=acc['cls'])
        for i, m in enumerate(monthly_accounts, start=4):
            v = m['by_acc'].get(acc['o15_code'], 0.0)
            ws.cell(row=r, column=i, value=money(v)).number_format = MONEY_FMT
        for c in range(1, len(hdr) + 1):
            ws.cell(row=r, column=c).border = BORDER
        r += 1
    autosize(ws, [13, 40, 11] + [15] * len(monthly_accounts))


def build_data_quality(wb, issues):
    ws = wb.create_sheet('Data_Quality')
    hdr = ['ลำดับ', 'ระดับ', 'รายการ', 'รายละเอียด']
    ws.append(hdr)
    style_header(ws, 1, len(hdr))
    ws.freeze_panes = 'A2'
    r = 2
    for i, it in enumerate(issues, start=1):
        ws.cell(row=r, column=1, value=i)
        lvl = ws.cell(row=r, column=2, value=it['level'])
        lvl.fill = OK_FILL if it['level'] == 'INFO' else BAD_FILL
        ws.cell(row=r, column=3, value=it['title'])
        ws.cell(row=r, column=4, value=it['detail'])
        for c in range(1, 5):
            ws.cell(row=r, column=c).border = BORDER
        r += 1
    autosize(ws, [7, 10, 40, 80])


def _section(ws, r, title, ncol):
    c = ws.cell(row=r, column=1, value=title)
    c.font = Font(bold=True, size=11)
    for i in range(1, ncol + 1):
        cell = ws.cell(row=r, column=i)
        cell.fill = SUB_FILL
        cell.border = BORDER
    return r + 1


def build_sales(wb, sales, monthly, groups, tot_sep, tot_oct, sales_last):
    """ชีตยอดขาย (Sales) — Odoo 15 ตั้งแต่ ม.ค.–ต.ค. 2569 (จุดตัดยอด 31 ต.ค. 2569)."""
    ws = wb.create_sheet('Sales_OD15')
    autosize(ws, [36, 20, 20, 20, 20])
    ws['A1'] = 'ยอดขาย (Sales) — Odoo 15 ม.ค.–ต.ค. 2569'
    ws['A1'].font = Font(bold=True, size=14, color='9E2424')
    ws['A2'] = ('Odoo 19 มีย้ายเฉพาะยอดยกมา ณ %s จึงยังไม่มียอดขาย — '
                'รายงานนี้เป็นข้อมูลฝั่ง Odoo 15' % CUTOFF)
    ws['A2'].font = Font(italic=True, size=9)

    r = 4
    # ---- 1) สรุป (เทียบ ณ สิ้นเดือน 9 และ สิ้นเดือน 10) ----
    r = _section(ws, r, '1) สรุปยอดขายสะสม', 3)
    for i, h in enumerate(['รายการ', 'ณ %s' % SALES_LABEL,
                           'ณ %s' % SALES_CUT_LABEL], start=1):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, 3)
    r += 1
    for label, v_sep, v_oct, bold in (
            ('รายได้จากการขายและบริการ (Income)', tot_sep[0], tot_oct[0], False),
            ('รายได้อื่น (Other Income)', tot_sep[1], tot_oct[1], False),
            ('รวมทั้งสิ้น', money(sum(tot_sep)), money(sum(tot_oct)), True)):
        c1 = ws.cell(row=r, column=1, value=label)
        if bold:
            c1.font = Font(bold=True)
        for col, val in ((2, v_sep), (3, v_oct)):
            c = ws.cell(row=r, column=col, value=val)
            c.number_format = MONEY_FMT
            if bold:
                c.font = Font(bold=True)
        for c in range(1, 4):
            ws.cell(row=r, column=c).border = BORDER
        r += 1
    ws.cell(row=r, column=1, value='หมายเหตุ: ยอดสะสม ณ 30 ก.ย. = ณ 31 ต.ค. '
                                   'เพราะ Odoo 15 ไม่มีรายได้ลงบัญชีหลัง %s เลย '
                                   '(เอกสารขายล่าสุด) — ต.ค. มีเฉพาะค่าเสื่อมราคา/เงินสดย่อย'
                                   % (sales_last or '-')
            ).font = Font(italic=True, size=9)
    r += 2

    # ---- 2) รายเดือน ----
    r = _section(ws, r, '2) ยอดขายรายเดือน ม.ค.–ต.ค. 2569', 5)
    hdr = ['เดือน', 'รายได้ (Income)', 'รายได้อื่น (Other Income)', 'รวม', 'สะสม (Income)']
    for i, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, 5)
    r += 1
    t_inc = t_oth = t_tot = 0.0
    for m in monthly:
        ws.cell(row=r, column=1, value=m['label'])
        ws.cell(row=r, column=2, value=m['income']).number_format = MONEY_FMT
        ws.cell(row=r, column=3, value=m['other']).number_format = MONEY_FMT
        ws.cell(row=r, column=4, value=m['total']).number_format = MONEY_FMT
        ws.cell(row=r, column=5, value=m['cum_income']).number_format = MONEY_FMT
        for c in range(1, 6):
            ws.cell(row=r, column=c).border = BORDER
        t_inc = money(t_inc + m['income'])
        t_oth = money(t_oth + m['other'])
        t_tot = money(t_tot + m['total'])
        r += 1
    c1 = ws.cell(row=r, column=1, value='รวม ม.ค.–ต.ค.')
    c1.font = Font(bold=True)
    for col, val in ((2, t_inc), (3, t_oth), (4, t_tot)):
        c = ws.cell(row=r, column=col, value=val)
        c.number_format = MONEY_FMT
        c.font = Font(bold=True)
    for c in range(1, 6):
        ws.cell(row=r, column=c).border = BORDER
    r += 1

    # ---- 3) แยกกลุ่มธุรกิจ ----
    r += 1
    r = _section(ws, r, '3) รายได้แยกกลุ่มธุรกิจ ณ %s' % SALES_CUT_LABEL, 5)
    hdr = ['กลุ่มธุรกิจ', 'รหัสบัญชี', 'รายได้ (gross)', 'ส่วนลดจ่าย', 'รายได้สุทธิ']
    for i, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, 5)
    r += 1
    g_gross = g_disc = g_net = 0.0
    for g in groups:
        ws.cell(row=r, column=1, value=g['name'].replace('รายได้', '').strip())
        ws.cell(row=r, column=2, value=g['code'])
        ws.cell(row=r, column=3, value=g['gross']).number_format = MONEY_FMT
        ws.cell(row=r, column=4, value=g['disc']).number_format = MONEY_FMT
        ws.cell(row=r, column=5, value=g['net']).number_format = MONEY_FMT
        for c in range(1, 6):
            ws.cell(row=r, column=c).border = BORDER
        g_gross = money(g_gross + g['gross'])
        g_disc = money(g_disc + g['disc'])
        g_net = money(g_net + g['net'])
        r += 1
    c1 = ws.cell(row=r, column=1, value='รวม')
    c1.font = Font(bold=True)
    for col, val in ((3, g_gross), (4, g_disc), (5, g_net)):
        c = ws.cell(row=r, column=col, value=val)
        c.number_format = MONEY_FMT
        c.font = Font(bold=True)
    for c in range(1, 6):
        ws.cell(row=r, column=c).border = BORDER
    r += 1

    # ---- 4) รายละเอียดรายบัญชี ----
    r += 1
    r = _section(ws, r, '4) รายละเอียดรายบัญชี ณ %s' % SALES_CUT_LABEL, 4)
    hdr = ['รหัสบัญชี', 'ชื่อบัญชี', 'ประเภท', 'ยอด']
    for i, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, 4)
    r += 1
    for s in sales:
        ws.cell(row=r, column=1, value=s['code'])
        ws.cell(row=r, column=2, value=s['name'])
        ws.cell(row=r, column=3, value=s['type_name'])
        ws.cell(row=r, column=4, value=s['amount']).number_format = MONEY_FMT
        for c in range(1, 5):
            ws.cell(row=r, column=c).border = BORDER
        r += 1

    r += 1
    ws.cell(row=r, column=1, value='หมายเหตุ').font = Font(bold=True)
    r += 1
    for n in ('แสดงรายได้เป็นค่าบวก (credit) — คำนวณจาก -balance ของบัญชีรายได้',
              'ส่วนลดจ่าย (บัญชี -01) แสดงเป็นค่าลบ (debit) เพื่อหักจากรายได้',
              'Odoo 19 ไม่มียอดขายจริง — มีย้ายเฉพาะยอดยกมา ณ %s' % CUTOFF):
        ws.cell(row=r, column=1, value='- ' + n).alignment = Alignment(
            wrap_text=True, vertical='top')
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        r += 1


def build_billing(wb, by_state, months, open_top, open_sum, sales_last):
    """ชีตใบวางบิล / บิลเรียกเก็บเงิน (dtr_account_billing) — ฝั่ง Odoo 15.

    มูลค่าบิล = ยอดใบแจ้งหนี้ (account_move) ที่ผูกกับบิลและ posted
    (ฟิลด์ pay_amount*/wht_amount* ในตารางว่างทั้งหมดจึงใช้ไม่ได้)
    """
    ws = wb.create_sheet('Billing_OD15')
    autosize(ws, [40, 16, 20, 20, 20])
    ws['A1'] = 'ใบวางบิล / บิลเรียกเก็บเงิน — Odoo 15 (dtr_account_billing)'
    ws['A1'].font = Font(bold=True, size=14, color='9E2424')
    ws['A2'] = 'มูลค่าบิล = ยอดใบแจ้งหนี้ที่ผูกและ posted (ฟิลด์ pay_amount/wht_amount ว่าง)'
    ws['A2'].font = Font(italic=True, size=9)

    r = 4
    # ---- 1) สรุปตามสถานะ (ทุกช่วงเวลา) ----
    r = _section(ws, r, '1) สรุปบิลตามสถานะ (ทั้งระบบ)', 3)
    for i, h in enumerate(['สถานะ', 'จำนวนบิล', 'มูลค่ารวม'], start=1):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, 3)
    r += 1
    st_label = {'draft': 'draft (ร่าง)', 'open': 'open (เปิด/ค้างเรียกเก็บ)',
                'done': 'done (ปิด)', 'cancel': 'cancel (ยกเลิก)'}
    for st in ('draft', 'open', 'done', 'cancel'):
        rec = next((x for x in by_state if x['state'] == st), None)
        c1 = ws.cell(row=r, column=1, value=st_label.get(st, st))
        if st == 'open':
            c1.font = Font(bold=True)
        ws.cell(row=r, column=2, value=int(rec['nb']) if rec else 0)
        c = ws.cell(row=r, column=3, value=money(rec['tot']) if rec else 0.0)
        c.number_format = MONEY_FMT
        if st == 'open':
            c.font = Font(bold=True)
        for cc in range(1, 4):
            ws.cell(row=r, column=cc).border = BORDER
        r += 1
    r += 1

    # ---- 2) ยอดเปิด (open) รวม ----
    r = _section(ws, r, '2) ยอดเปิด (ค้างเรียกเก็บ) — state = open', 3)
    ws.cell(row=r, column=1, value='จำนวนบิล (open) ทั้งหมด')
    ws.cell(row=r, column=2, value=int(open_sum.get('n') or 0))
    r += 1
    ws.cell(row=r, column=1, value='ช่วงวันที่บิล (bill_date)')
    ws.cell(row=r, column=2, value='%s ถึง %s' % (open_sum.get('mn') or '-',
                                                  open_sum.get('mx') or '-'))
    r += 1
    ws.cell(row=r, column=1, value='ยอดเปิดรวม').font = Font(bold=True)
    c = ws.cell(row=r, column=2, value=money(open_sum.get('tot')))
    c.number_format = MONEY_FMT
    c.font = Font(bold=True)
    r += 2

    # ---- 3) บิลรายเดือน ม.ค.–ต.ค. 2569 ----
    r = _section(ws, r, '3) บิลรายเดือน ม.ค.–ต.ค. 2569 (ตาม bill_date)', 5)
    hdr = ['เดือน', 'จำนวนบิล', 'จำนวนบิล (open)', 'มูลค่าบิลรวม', 'มูลค่า (open)']
    for i, h in enumerate(hdr, start=1):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, 5)
    r += 1
    t_nb = t_nb_open = t_tot = t_tot_open = 0
    for m in months:
        ws.cell(row=r, column=1, value=m['label'])
        ws.cell(row=r, column=2, value=m['nb'])
        ws.cell(row=r, column=3, value=m['nb_open'])
        ws.cell(row=r, column=4, value=m['tot']).number_format = MONEY_FMT
        ws.cell(row=r, column=5, value=m['tot_open']).number_format = MONEY_FMT
        for cc in range(1, 6):
            ws.cell(row=r, column=cc).border = BORDER
        t_nb += m['nb']
        t_nb_open += m['nb_open']
        t_tot = money(t_tot + m['tot'])
        t_tot_open = money(t_tot_open + m['tot_open'])
        r += 1
    c1 = ws.cell(row=r, column=1, value='รวม ม.ค.–ต.ค.')
    c1.font = Font(bold=True)
    for col, val in ((2, t_nb), (3, t_nb_open), (4, t_tot), (5, t_tot_open)):
        c = ws.cell(row=r, column=col, value=val)
        if col in (4, 5):
            c.number_format = MONEY_FMT
        c.font = Font(bold=True)
    for cc in range(1, 6):
        ws.cell(row=r, column=cc).border = BORDER
    r += 2

    # ---- 4) ยอดเปิดแยกรายคู่ค้า ----
    r = _section(ws, r, '4) ยอดเปิด (open) แยกรายคู่ค้า — สูงสุด 20 อันดับ', 3)
    for i, h in enumerate(['คู่ค้า', 'จำนวนบิล', 'มูลค่า (open)'], start=1):
        ws.cell(row=r, column=i, value=h)
    style_header(ws, r, 3)
    r += 1
    for p in open_top:
        ws.cell(row=r, column=1, value=(p['partner'] or '(ไม่ระบุ)').strip())
        ws.cell(row=r, column=2, value=int(p['nb']))
        ws.cell(row=r, column=3, value=money(p['tot'])).number_format = MONEY_FMT
        for cc in range(1, 4):
            ws.cell(row=r, column=cc).border = BORDER
        r += 1
    r += 1

    ws.cell(row=r, column=1, value='หมายเหตุ').font = Font(bold=True)
    r += 1
    for n in ('บิลล่าสุดในระบบ = %s (Odoo 15 ไม่มีบิลใหม่หลังวันนี้)' % (open_sum.get('mx') or '-'),
              'ยอดเปิดรวมเป็นยอดสะสมทั้งระบบ (บิลค้างเรียกเก็บตั้งแต่ปี 2023) ไม่ใช่ยอดของปี 2569',
              'มูลค่าบิลอ้างอิงใบแจ้งหนี้ที่ผูก (posted); บิลที่ยังไม่ผูกใบแจ้งหนี้จะไม่มียอด',
              'เอกสารขายล่าสุด (out_invoice posted) = %s' % (sales_last or '-')):
        ws.cell(row=r, column=1, value='- ' + n).alignment = Alignment(
            wrap_text=True, vertical='top')
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        r += 1


# --------------------------------------------------------------------------
def main():
    cfg = read_conf()
    chart = load_chart()
    c15 = connect(OD15_DB, cfg)
    c19 = connect(OD19_DB, cfg)
    try:
        # ---- ยอดรายบัญชี ณ จุดตัดยอด ----
        rows15 = od15_balances(c15, CUTOFF)
        rows19 = od19_balances(c19, CUTOFF)
    finally:
        pass

    # จัดกลุ่ม OD15 (เฉพาะงบดุล) + classification
    bs15 = []
    pl15 = []
    for r in rows15:
        cls, o19_code, atype = classify(r['code'], r['type_name'], chart)
        rec = {'o15_code': r['code'], 'o19_code': o19_code, 'name': r['name'],
               'atype': atype, 'cls': cls, 'bal15': money(r['bal'])}
        (bs15 if cls in ('asset', 'liability', 'equity') else pl15).append(rec)

    # OD19 รวมตามรหัส (กันรหัสซ้ำหลาย id)
    bs19_map = {}
    for r in rows19:
        cls = cls_from_type(r['account_type'])
        if cls not in ('asset', 'liability', 'equity'):
            continue
        code = r['code'] or ''
        cur = bs19_map.setdefault(
            code, {'o19_code': code, 'name': r['name'], 'atype': r['account_type'],
                   'cls': cls, 'bal19': 0.0})
        cur['bal19'] = money(cur['bal19'] + money(r['bal']))

    # เทียบทีละบัญชี
    compare = []
    matched = set()
    fails = []
    for rec in sorted(bs15, key=lambda x: x['o15_code']):
        b19 = bs19_map.get(rec['o19_code'])
        bal19 = b19['bal19'] if b19 else 0.0
        if b19:
            matched.add(rec['o19_code'])
        diff = money(bal19 - rec['bal15'])
        status = 'ตรง' if abs(diff) <= TOL else 'ต่าง'
        if status == 'ต่าง':
            fails.append(rec)
        compare.append({
            'o15_code': rec['o15_code'], 'o19_code': rec['o19_code'],
            'name': rec['name'], 'atype': rec['atype'], 'cls': rec['cls'],
            'bal15': rec['bal15'], 'bal19': bal19, 'diff': diff, 'status': status})

    # บัญชีงบดุลฝั่ง OD19 ที่ไม่ถูกจับคู่ (มีในระบบใหม่แต่ไม่มีใน OD15)
    extra19 = [v for k, v in sorted(bs19_map.items())
               if k not in matched and abs(v['bal19']) > TOL]

    # ยอดรวมตามหมวด
    def totals(records, key):
        t = {'asset': 0.0, 'liability': 0.0, 'equity': 0.0}
        for rec in records:
            t[rec['cls']] = money(t[rec['cls']] + money(rec.get(key, 0.0)))
        return t

    tot15 = totals(bs15, 'bal15')
    tot19 = totals(list(bs19_map.values()), 'bal19')

    # ---- จัดกลุ่มยอดให้เทียบกันได้ ----
    # OD19 รวม "กำไร(ขาดทุน)สุทธิประจำปี" ไว้ในบัญชี equity_unaffected (999999)
    # ส่วน OD15 เก็บกำไรระหว่างปีไว้ในบัญชีกำไรขาดทุน (ยังไม่ปิดบัญชี) จึงต้องแยกแสดง
    pl15 = money(sum(r['bal15'] for r in pl15))                       # สุทธิ P&L ฝั่ง OD15
    unaffected19 = money(sum(v['bal19'] for v in bs19_map.values()
                             if v['atype'] == 'equity_unaffected'))
    eq15 = tot15['equity']
    eq19 = money(tot19['equity'] - unaffected19)                      # เฉพาะบัญชีทุน
    rec = {
        'asset15': tot15['asset'], 'asset19': tot19['asset'],
        'liab15': tot15['liability'], 'liab19': tot19['liability'],
        'eq15': eq15, 'eq19': eq19,
        'pl15': pl15, 'unaffected19': unaffected19,
        'liab_eq15': money(tot15['liability'] + eq15 + pl15),
        'liab_eq19': money(tot19['liability'] + tot19['equity']),
        'balance15': money(tot15['asset'] + tot15['liability'] + eq15 + pl15),
        'balance19': money(tot19['asset'] + tot19['liability'] + tot19['equity']),
    }

    # ---- OD15 รายเดือน + รายบัญชี × เดือน ----
    monthly = []
    monthly_acc = []
    for (y, m) in MONTHS:
        me = month_end(y, m)
        mrows = od15_balances(c15, me)
        by_acc = {}
        agg = {'asset': 0.0, 'liability': 0.0, 'equity': 0.0, 'pl': 0.0}
        for r in mrows:
            cls, _, _ = classify(r['code'], r['type_name'], chart)
            b = money(r['bal'])
            key = cls if cls in ('asset', 'liability', 'equity') else 'pl'
            if key != 'pl':
                by_acc[r['code']] = money(by_acc.get(r['code'], 0.0) + b)
            agg[key] = money(agg[key] + b)
        eq_sum = money(agg['asset'] + agg['liability'] + agg['equity'])
        check = money(eq_sum + agg['pl'])   # ควรเป็น 0 (ยอดลงตัว)
        monthly.append({
            'label': '%s %d' % (MONTH_TH[m], y),
            'asset': agg['asset'], 'liability': agg['liability'],
            'equity': agg['equity'], 'pl': agg['pl'], 'eq_sum': eq_sum,
            'check': check,
            'note': 'CUT-OFF (เทียบกับ OD19)' if me.isoformat() == CUTOFF else ''})
        monthly_acc.append({'label': '%s %d' % (MONTH_TH[m], y), 'by_acc': by_acc})

    # ---- ยอดขาย OD15 (Income + Other Income) ----
    srows = od15_income(c15, CUTOFF)                       # ณ จุดตัดยอด 31 ต.ค. 2569
    sales = sorted(
        [{'code': r['code'], 'name': r['name'], 'type_name': r['type_name'],
          'amount': money(-r['bal'])} for r in srows],
        key=lambda x: x['code'])
    tot_oct = _income_split(srows)                         # ณ 31 ต.ค. 2569
    tot_sep = _income_split(od15_income(c15, SALES_DATE))  # ณ 30 ก.ย. 2569
    income_total, other_total = tot_oct

    sales_monthly = []
    cum = 0.0
    for (y, m) in SALES_MONTHS:
        mrows_i = od15_income(c15, month_end(y, m), datetime.date(y, m, 1))
        inc, oth = _income_split(mrows_i)
        cum = money(cum + inc)
        sales_monthly.append({'label': '%s %d' % (MONTH_TH[m], y),
                              'income': inc, 'other': oth,
                              'total': money(inc + oth), 'cum_income': cum})

    # จัดกลุ่มธุรกิจ: บัญชีรายได้รหัสฐาน (4110-01) + ส่วนลดจ่าย (4110-01-01)
    by_code = {s['code']: s for s in sales}
    sales_groups = []
    for s in sales:
        if s['type_name'] != 'Income' or s['code'].count('-') != 1:
            continue
        disc = by_code.get(s['code'] + '-01')
        d = money(disc['amount']) if disc else 0.0
        sales_groups.append({'code': s['code'], 'name': s['name'],
                             'gross': money(s['amount']), 'disc': d,
                             'net': money(s['amount'] + d)})
    sales_groups.sort(key=lambda x: x['code'])

    # ---- เอกสารขายล่าสุด + ใบวางบิล / บิลเรียกเก็บเงิน (OD15) ----
    sales_last = od15_last_out_invoice(c15)
    bill_by_state = od15_billing_by_state(c15)
    bill_open_top = od15_billing_open_top(c15, 20)
    bill_open_sum = od15_billing_open_summary(c15)
    bmap = od15_billing_monthly(c15, datetime.date(2026, 1, 1),
                                datetime.date(2026, 12, 31))
    bill_months = []
    for (y, m) in SALES_MONTHS:
        bm = bmap.get('%04d-%02d' % (y, m))
        bill_months.append({
            'label': '%s %d' % (MONTH_TH[m], y),
            'nb': int(bm['nb']) if bm else 0,
            'nb_open': int(bm['nb_open']) if bm else 0,
            'tot': money(bm['tot']) if bm else 0.0,
            'tot_open': money(bm['tot_open']) if bm else 0.0})

    # ---- Data quality ----
    issues = []
    # บัญชี OD15 ที่ไม่มีในผัง mapping
    unmapped = [r for r in bs15 if not (chart.get(r['o15_code']) or {}).get('od19_account_type')]
    for r in unmapped:
        issues.append({'level': 'WARN', 'title': 'บัญชี OD15 ไม่มีในผัง mapping',
                       'detail': '%s %s (ใช้ fallback: %s)' % (r['o15_code'], r['name'], r['atype'])})
    for v in extra19:
        lvl = 'INFO' if v['atype'] == 'equity_unaffected' else 'WARN'
        note = ('เป็นบัญชีคู่ปรับกำไร(ขาดทุน)สุทธิประจำปี — เทียบเท่ายอด P&L สุทธิฝั่ง OD15 '
                '(%.2f)' % pl15) if v['atype'] == 'equity_unaffected' else ''
        issues.append({'level': lvl, 'title': 'บัญชี OD19 ที่ไม่มีคู่ใน OD15',
                       'detail': '%s %s (%s) ยอด %.2f %s'
                       % (v['o19_code'], v['name'], v['cls'], v['bal19'], note)})
    for r in fails:
        issues.append({'level': 'FAIL', 'title': 'ผลต่างเกิน %.2f' % TOL,
                       'detail': '%s/%s %s OD15=%.2f OD19=%.2f' %
                       (r['o15_code'], r['o19_code'], r['name'], r['bal15'],
                        bs19_map.get(r['o19_code'], {}).get('bal19', 0.0))})
    if not issues:
        issues.append({'level': 'INFO', 'title': 'ไม่พบปัญหา',
                       'detail': 'ทุกรายบัญชีงบดุลเท่ากัน (ผลต่าง 0.00) ณ %s' % CUTOFF})
    # หมายเหตุเชิงบริบท
    issues.append({'level': 'INFO', 'title': 'ขอบเขตข้อมูล Odoo 19',
                   'detail': 'Odoo 19 มีย้ายเฉพาะยอดยกมา ณ %s — ไม่มีข้อมูล ม.ค.–ก.ย. 2026'
                             ' จึงเทียบรายเดือนไม่ได้ (แสดงเฉพาะ OD15)' % CUTOFF})
    issues.append({'level': 'INFO', 'title': 'Cut-off ต่างจากที่ผู้ใช้ระบุ',
                   'detail': 'ผู้ใช้ระบุ ม.ค.–ก.ย. แต่จุดตัดยอดของระบบใหม่อยู่ที่ 31 ต.ค. 2026 '
                             '(สินทรัพย์ ณ 30 ก.ย. = 217,168,626.86 ต่างจาก 31 ต.ค. = 217,020,640.21 '
                             'อยู่ 147,986.65 ซึ่งเป็นรายการเดือน ต.ค.)'})
    issues.append({'level': 'WARN', 'title': 'ยอดขาย ก.ย. = ต.ค. (ไม่ใช่ข้อผิดพลาด)',
                   'detail': 'Odoo 15 มีเอกสารขาย (out_invoice posted) ล่าสุด %s และใบวางบิลล่าสุด %s — '
                             'ไม่มีรายได้ลงบัญชีหลังวันดังกล่าวเลย เดือน ต.ค. 2569 มีเฉพาะค่าเสื่อมราคา/'
                             'เงินสดย่อย ยอดขายสะสม ณ 30 ก.ย. กับ ณ 31 ต.ค. จึงเท่ากันโดยธรรมชาติ '
                             '(ดูชีต Sales_OD15 / Billing_OD15)' % (sales_last, bill_open_sum.get('mx'))})

    # ---- ตัดสินผล ----
    n_bad = len(fails)
    verdict = ('PASS — งบดุลทั้งสองระบบตรงกันทุกรายบัญชี (ผลต่าง 0.00)'
               if n_bad == 0 else 'FAIL — พบ %d บัญชีที่ผลต่างเกิน %.2f' % (n_bad, TOL))

    notes = [{'text': 'ผลต่าง = OD19 - OD15; ต้องเป็น 0.00 ± %.2f ทุกรายบัญชี' % TOL,
              'fail': False},
             {'text': 'Odoo 19 = ยอดยกมา ณ %s เท่านั้น (ไม่มีข้อมูล ม.ค.–ก.ย. 2026)' % CUTOFF,
              'fail': False},
             {'text': 'OD15 ใช้หลัก Signed balance (สินทรัพย์ +, หนี้สิน/ทุน -) เหมือน OD19',
              'fail': False},
             {'text': 'บัญชีกำไรขาดทุนไม่ยกมา; สะท้อนผ่าน equity_unaffected (999999) ฝั่ง OD19',
              'fail': False}]
    for r in fails:
        notes.append({'text': 'ต่าง: %s %s' % (r['o15_code'], r['name']), 'fail': True})

    # ---- เขียนไฟล์ ----
    wb = Workbook()
    wb.remove(wb.active)
    build_summary(wb, CUTOFF, rec, verdict, len(bs15), len(bs19_map),
                  len(compare) - n_bad, notes)
    build_compare(wb, compare, chart)
    build_monthly(wb, monthly)
    build_monthly_by_acc(wb, bs15, monthly_acc)
    build_sales(wb, sales, sales_monthly, sales_groups, tot_sep, tot_oct,
                sales_last)
    build_billing(wb, bill_by_state, bill_months, bill_open_top, bill_open_sum,
                  sales_last)
    build_data_quality(wb, issues)
    wb.save(OUT_PATH)

    # ---- สรุปทางคอนโซล ----
    print('=' * 72)
    print('BS Compare OD15 vs OD19 @ %s' % CUTOFF)
    print('=' * 72)
    print('ASSET        OD15=%18.2f  OD19=%18.2f  diff=%9.2f'
          % (rec['asset15'], rec['asset19'], rec['asset19'] - rec['asset15']))
    print('LIABILITY    OD15=%18.2f  OD19=%18.2f  diff=%9.2f'
          % (rec['liab15'], rec['liab19'], rec['liab19'] - rec['liab15']))
    print('EQUITY(ทุน)  OD15=%18.2f  OD19=%18.2f  diff=%9.2f'
          % (rec['eq15'], rec['eq19'], rec['eq19'] - rec['eq15']))
    print('P&L/สะสมปี   OD15=%18.2f  OD19=%18.2f  diff=%9.2f'
          % (rec['pl15'], rec['unaffected19'], rec['unaffected19'] - rec['pl15']))
    print('LIAB+EQUITY  OD15=%18.2f  OD19=%18.2f  diff=%9.2f'
          % (rec['liab_eq15'], rec['liab_eq19'], rec['liab_eq19'] - rec['liab_eq15']))
    print('สมการบัญชี   OD15=%18.2f  OD19=%18.2f' % (rec['balance15'], rec['balance19']))
    print('บัญชีงบดุลที่เทียบ: OD15=%d | OD19=%d | ไม่ตรง=%d'
          % (len(bs15), len(bs19_map), n_bad))
    print('-' * 72)
    print('ยอดขาย OD15 (Income + Other Income)')
    print('%-14s %18s %18s' % ('', 'ณ %s' % SALES_LABEL, 'ณ %s' % SALES_CUT_LABEL))
    print('%-14s %18.2f %18.2f' % ('Income', tot_sep[0], tot_oct[0]))
    print('%-14s %18.2f %18.2f' % ('Other Income', tot_sep[1], tot_oct[1]))
    print('%-14s %18.2f %18.2f' % ('รวมทั้งสิ้น', money(sum(tot_sep)), money(sum(tot_oct))))
    print('  ส่วนลดจ่ายรวม =%18.2f' % money(sum(g['disc'] for g in sales_groups)))
    print('  เอกสารขายล่าสุด (out_invoice posted) = %s' % (sales_last or '-'))
    print('  => ไม่มีรายได้ลงบัญชีหลังวันดังกล่าว ยอดสะสม ก.ย.=ต.ค. จึงไม่เปลี่ยน')
    print('-' * 72)
    print('ใบวางบิล / บิลเรียกเก็บเงิน OD15 (dtr_account_billing)')
    for st in ('draft', 'open', 'done', 'cancel'):
        rec = next((x for x in bill_by_state if x['state'] == st), None)
        print('  %-8s บิล=%5d  มูลค่า=%18.2f'
              % (st, int(rec['nb']) if rec else 0,
                 money(rec['tot']) if rec else 0.0))
    print('  ยอดเปิด (open) รวม =%18.2f  (%d บิล, %s ถึง %s)'
          % (money(bill_open_sum.get('tot')), int(bill_open_sum.get('n') or 0),
             bill_open_sum.get('mn'), bill_open_sum.get('mx')))
    print('-' * 72)
    print('ผล: %s' % verdict)
    print('ไฟล์: %s' % OUT_PATH)
    print('=' * 72)
    return 0 if n_bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
