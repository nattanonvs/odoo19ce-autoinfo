# -*- coding: utf-8 -*-
"""s11_outstanding_real_docs — สร้าง "เอกสารจริง" ลูกหนี้/เจ้าหนี้คงค้าง ณ วันตัดยอด

บริบท (ยืนยันกับผู้ใช้แล้ว):
    puat เดิมมียอด AR/AP สูงเกินจริง ~2 เท่า เพราะมี *สองชั้นข้อมูล* ที่ซ้ำกัน
      1) ชุดเอกสารจริงที่ replicate มาจาก od15 (sim_replicate_gl15.py)
         External ID = __import15__.account_move.gl15rep_<od15 move id>
         (typed invoice 1:1 + entry) — สร้างไว้เพื่อเทียบรายงาน od15/od19
         แต่ "ไม่ได้ reconcile" จึงค้างเป็นยอด gross ทั้งก้อน
      2) JE ยอดยกมา AR/AP ต่อคู่ค้า (s08_opening → BRF/2026/0001..0124)
         External ID = __import15__.account_move.arap_<partner_id>

ขั้นตอนนี้จึง:
    (0) ลบ gl15rep_* ทั้งชุด (ตามที่ผู้ใช้ยืนยัน: "ลบ gl15rep ทั้งชุด")
    (1) ลบ arap_* (BRF/2026/0001..0124) เท่านั้น — เก็บ BRF/2026/0125 (opening.gl) ไว้
    (2) สร้าง "ใบจริง" ต่อใบตาม od15 (out_invoice/out_refund/in_invoice/in_refund)
        วันที่เดิม + เลขที่เดิม + คู่ค้าจริง | ยอด = residual as-of 2026-10-31
        บรรทัดหลัก (non-AR/AP) ใช้บัญชีคู่ปรับ 999999 (equity_unaffected)
    (3) สร้าง JE ต่อคู่ค้า สำหรับ residual ของ move_type='entry'
        (od15 บันทึกการชำระเงินเป็น entry → ยอดค้างต้องนับรวม entry)
    (4) Gate: ยอดรวม AR/AP ต้อง tie Target ณ 2026-10-31
        AR  32,442,103.01
        AP -16,081,136.61

กติกา residual as-of (เหมือน probe ทุกตัวในเซสชันนี้):
    sum(debit - credit)
      + (partial reconcile ฝั่ง debit ที่เกิดหลังวันเป้าหมาย)
      - (partial reconcile ฝั่ง credit ที่เกิดหลังวันเป้าหมาย)

การรันซ้ำ (idempotent):
    * การลบ (0)(1) รันซ้ำได้ (รอบหลังจะไม่พบเป้าหมาย)
    * เอกสารจริงผูก External ID __import15__.account_move.realdoc_<od15 move id>
    * JE entry ผูก External ID __import15__.account_move.entryresid_<partner id|nopartner>
    * ใบที่ post แล้วจะถูกข้ามเมื่อรันซ้ำ

ตัวแปรสภาพแวดล้อม: MIG_DRY_RUN=1 (ไม่เขียนจริง), S11_PURGE=0 (ข้ามการลบ; ค่าเริ่มต้น=ลบ)
"""
import os

import common
import legacy

# วันตัดยอด (ให้ตรงกับ s08_opening)
OPENING_DATE = '2026-10-31'

# สมุดรายวันของใบจริงและ JE
SALE_JOURNAL = 'INV'
PURCHASE_JOURNAL = 'BILL'
ENTRY_JOURNAL = 'BRF'

# ประเภทใบจริง
INVOICE_TYPES = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
PURCHASE_TYPES = ('in_invoice', 'in_refund')

# ทิศทางของ Odoo 19 (account.move.direction_sign):
#   +1 = in_invoice / out_refund   |   -1 = out_invoice / in_refund
# บรรทัด AR/AP ที่ Odoo สร้างอัตโนมัติมียอดคงเหลือ = -direction_sign * price_unit
# จึงต้องตั้ง price_unit = -direction_sign * resid เพื่อให้ยอดคงเหลือเท่ากับ resid จริง
_DIRECTION_SIGN = {
    'out_invoice': -1,
    'in_refund': -1,
    'in_invoice': 1,
    'out_refund': 1,
}

# เมื่อ residual มีเครื่องหมายตรงข้ามกับธรรมชาติของใบ (เช่น in_invoice แต่ AP ติดเดบิต)
# Odoo ห้าม post ใบที่มี amount_total ติดลบ → ต้องออกเป็นใบลดหนี้ (credit note) แทน
_REFUND_OF = {
    'out_invoice': 'out_refund',
    'in_invoice': 'in_refund',
}

# ยอดเป้าหมาย (ใช้เป็น gate)
TARGET_AR = 32442103.01
TARGET_AP = -16081136.61

# คำนำหน้า External ID (คีย์จะถูก slug+hash โดย common.get_xmlid)
DOC_TAG = 'realdoc'
ENTRY_TAG = 'entryresid'

PURGE = os.environ.get('S11_PURGE', '1') != '0'


# --------------------------------------------------------------------------
# ตัวช่วยอ้างอิงฝั่ง Odoo 19
# --------------------------------------------------------------------------
def _account(env, od15_code):
    xmlid = common.get_xmlid('account.account', od15_code)
    acc_id = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    return env['account.account'].browse(acc_id) if acc_id else None


def _partner(env, legacy_id):
    if not legacy_id:
        return None
    xmlid = common.get_xmlid('res.partner', legacy_id)
    pid = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    return env['res.partner'].browse(pid) if pid else None


def _journal(env, code):
    return env['account.journal'].search(
        [('code', '=', code), ('company_id', '=', env.company.id)], limit=1)


def _offset_account(env):
    acc = env['account.account'].search(
        [('account_type', '=', 'equity_unaffected')], limit=1)
    if not acc:
        raise ValueError("ไม่พบบัญชีคู่ปรับ Current Year Earnings (equity_unaffected)")
    return acc


# --------------------------------------------------------------------------
# การอ่านฝั่ง od15 (read-only)
# --------------------------------------------------------------------------
# นิพจน์ residual as-of ใช้ซ้ำทั้งสองคิวรี
_RESID = (
    "l.debit - l.credit "
    "+ COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p "
    "            JOIN account_move_line cl ON cl.id = p.debit_move_id "
    "            JOIN account_move cm ON cm.id = cl.move_id "
    "            WHERE p.credit_move_id = l.id AND cm.date <= %(d)s::date), 0) "
    "- COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p "
    "            JOIN account_move_line cl ON cl.id = p.credit_move_id "
    "            JOIN account_move cm ON cm.id = cl.move_id "
    "            WHERE p.debit_move_id = l.id AND cm.date <= %(d)s::date), 0)"
)


def _fetch_real_docs():
    """ใบจริง (out_invoice/out_refund/in_invoice/in_refund) ที่ residual<>0 ณ วันตัดยอด."""
    sql = (
        "SELECT * FROM ("
        "  SELECT m.id AS move_id, m.name, m.ref, m.date, m.move_type, "
        "         m.partner_id, a.code AS account_code, "
        "         round(sum(" + _RESID + ")::numeric, 2) AS resid "
        "  FROM account_move_line l "
        "  JOIN account_move m ON m.id = l.move_id "
        "  JOIN account_account a ON a.id = l.account_id "
        "  JOIN account_account_type t ON t.id = a.user_type_id "
        "  WHERE m.state = 'posted' AND m.date <= %(d)s::date "
        "    AND t.type IN ('receivable', 'payable') "
        "    AND m.move_type IN ('out_invoice', 'out_refund', "
        "                        'in_invoice', 'in_refund') "
        "  GROUP BY 1,2,3,4,5,6,7"
        ") s WHERE s.resid <> 0 "
        "ORDER BY s.date, s.move_id"
    )
    return legacy.fetch_all(sql, {'d': OPENING_DATE})


def _fetch_entry_resid():
    """residual ของ move_type='entry' ต่อ (partner, account, ประเภทบัญชี)."""
    sql = (
        "SELECT * FROM ("
        "  SELECT l.partner_id, a.code AS account_code, t.type AS atype, "
        "         round(sum(" + _RESID + ")::numeric, 2) AS resid "
        "  FROM account_move_line l "
        "  JOIN account_move m ON m.id = l.move_id "
        "  JOIN account_account a ON a.id = l.account_id "
        "  JOIN account_account_type t ON t.id = a.user_type_id "
        "  WHERE m.state = 'posted' AND m.date <= %(d)s::date "
        "    AND t.type IN ('receivable', 'payable') "
        "    AND m.move_type = 'entry' "
        "  GROUP BY 1,2,3"
        ") s WHERE s.resid <> 0 "
        "ORDER BY s.partner_id, s.account_code"
    )
    return legacy.fetch_all(sql, {'d': OPENING_DATE})


# --------------------------------------------------------------------------
# (0)(1) ลบชั้นข้อมูลซ้ำ
# --------------------------------------------------------------------------
def _purge_by_xmlid(env, name_like, label, stats):
    imd = env['ir.model.data']
    xmlids = imd.search([
        ('module', '=', common.MODULE_PREFIX),
        ('model', '=', 'account.move'),
        ('name', 'like', name_like),
    ])
    moves = env['account.move'].browse([x.res_id for x in xmlids])
    n = len(moves)
    common.log("%s: พบ %d ใบ" % (label, n))
    if not n:
        return 0
    if common.DRY_RUN:
        common.log("[DRY-RUN] จะลบ %s %d ใบ" % (label, n))
        stats.skipped += n
        return n
    posted = moves.filtered(lambda m: m.state == 'posted')
    if posted:
        posted.button_draft()
    moves.unlink()
    imd.browse(xmlids.ids).unlink()
    stats.updated += n
    common.log("%s: ลบแล้ว %d ใบ" % (label, n))
    return n


def _purge_duplicates(env, stats):
    if not PURGE:
        common.log("S11_PURGE=0 — ข้ามการลบชั้นข้อมูลซ้ำ")
        return
    _purge_by_xmlid(env, 'account_move.gl15rep\\_%', 'ลบชุด replicate (gl15rep)', stats)
    _purge_by_xmlid(env, 'account_move.arap\\_%', 'ลบ JE ยอดยกมาเดิม (arap/BRF)', stats)


# --------------------------------------------------------------------------
# (2) สร้างใบจริง
# --------------------------------------------------------------------------
def _post_move(env, key, vals, stats):
    """สร้าง + post เอกสารพร้อมผูก External ID (idempotent)."""
    xmlid = common.get_xmlid('account.move', key)
    # '_amount' เป็นเพียงตัวช่วย log ของ dry-run — ต้องถอดออกก่อนสร้างจริง
    amount = vals.pop('_amount', 0.0)
    if common.DRY_RUN:
        common.log("[DRY-RUN] จะสร้าง %s | %s %s %.2f"
                   % (xmlid, vals.get('move_type'), vals.get('date'), amount))
        stats.skipped += 1
        return None
    imd = env['ir.model.data']
    existing = imd._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    if existing:
        rec = env['account.move'].browse(existing)
        if rec.state == 'posted':
            stats.skipped += 1
            return rec
        rec.unlink()
    move = env['account.move'].with_context(
        od19_skip_86_4_validation=True).create(vals)
    if move.move_type in PURCHASE_TYPES and move.tax_invoice_ids:
        move.tax_invoice_ids.write({
            'tax_invoice_number': vals.get('ref') or vals.get('name') or '/',
            'tax_invoice_date': vals.get('invoice_date') or vals.get('date'),
        })
    move.action_post()
    imd._update_xmlids(
        [{'xml_id': xmlid, 'record': move, 'noupdate': True}], update=True)
    stats.created += 1
    return move


def _create_real_docs(env, stats):
    offset = _offset_account(env)
    rows = _fetch_real_docs()
    total = 0.0
    by_type = {}
    errors = 0
    for r in rows:
        partner = _partner(env, r['partner_id'])
        if not partner:
            common.log("คำเตือน: ไม่พบคู่ค้าสำหรับใบเดิม id=%s (%s)"
                       % (r['move_id'], r['name']))
            errors += 1
            continue
        acc = _account(env, r['account_code'])
        if not acc:
            common.log("คำเตือน: ไม่พบบัญชี OD19 รหัสเดิม %s" % r['account_code'])
            errors += 1
            continue
        is_purchase = r['move_type'] in PURCHASE_TYPES
        amount = round(float(r['resid']), 2)
        # ตั้งราคาต่อหน่วยให้บรรทัด AR/AP ที่ Odoo สร้างมียอดคงเหลือ = resid จริง
        move_type = r['move_type']
        price_unit = round(-_DIRECTION_SIGN[move_type] * amount, 2)
        if price_unit < 0 and move_type in _REFUND_OF:
            # resid ตรงข้ามกับธรรมชาติของใบ → ออกเป็นใบลดหนี้แทน (Odoo ห้ามใบยอดติดลบ)
            move_type = _REFUND_OF[move_type]
            price_unit = round(-price_unit, 2)
            is_purchase = move_type in PURCHASE_TYPES
            common.log("ปรับเป็นใบลดหนี้: %s -> %s (resid=%.2f)"
                       % (r['move_type'], move_type, amount))
        journal = _journal(env, PURCHASE_JOURNAL if is_purchase else SALE_JOURNAL)
        if not journal:
            common.log("คำเตือน: ไม่พบสมุดรายวัน %s" % (
                PURCHASE_JOURNAL if is_purchase else SALE_JOURNAL))
            errors += 1
            continue
        # ตั้งบัญชีคุม AR/AP ของคู่ค้าให้ตรงกับบัญชีที่ od15 ใช้จริงในใบนี้
        field = ('property_account_payable_id' if is_purchase
                 else 'property_account_receivable_id')
        if partner.with_company(env.company)[field] != acc:
            partner.with_company(env.company)[field] = acc

        name = (r['name'] or '').strip() or ('/%s' % r['move_id'])
        vals = {
            'move_type': move_type,
            'partner_id': partner.id,
            'journal_id': journal.id,
            'date': r['date'],
            'invoice_date': r['date'],
            'name': name,
            'ref': (r['ref'] or name),
            'invoice_line_ids': [(0, 0, {
                'account_id': offset.id,
                'name': 'ยอดค้าง ณ %s (อ้างอิง %s)' % (OPENING_DATE, name),
                'quantity': 1.0,
                'price_unit': price_unit,
                'tax_ids': [(6, 0, [])],
            })],
            '_amount': amount,
        }
        try:
            _post_move(env, '%s.%s' % (DOC_TAG, r['move_id']), vals, stats)
        except Exception as exc:  # noqa: BLE001
            common.log("ล้มเหลว %s %s: %s"
                       % (r['move_type'], name, str(exc).splitlines()[0]))
            errors += 1
            continue
        total += amount
        by_type[r['move_type']] = by_type.get(r['move_type'], 0) + 1
    if errors:
        stats.error += errors
    common.log("ใบจริง: %d ใบ %s | ยอดสุทธิ=%.2f (errors=%d)"
               % (len(rows), by_type, total, errors))


# --------------------------------------------------------------------------
# (3) JE ต่อคู่ค้า สำหรับ residual ของ entry
# --------------------------------------------------------------------------
def _create_entry_residual(env, stats):
    journal = _journal(env, ENTRY_JOURNAL)
    if not journal:
        raise ValueError("ไม่พบสมุดรายวัน '%s' สำหรับ JE residual ของ entry" % ENTRY_JOURNAL)
    offset = _offset_account(env)

    grouped = {}      # partner_id -> list[(account, resid)]
    no_partner = []
    unknown = 0
    for r in _fetch_entry_resid():
        acc = _account(env, r['account_code'])
        if not acc:
            common.log("คำเตือน: ไม่พบบัญชี OD19 รหัสเดิม %s (entry residual)"
                       % r['account_code'])
            unknown += 1
            continue
        item = (acc, round(float(r['resid']), 2))
        if r['partner_id'] is None:
            no_partner.append(item)
        else:
            grouped.setdefault(r['partner_id'], []).append(item)
    if unknown:
        stats.error += unknown

    def _emit(key, items, ref):
        lines = []
        net = 0.0
        for acc, resid in items:
            lines.append((0, 0, {
                'account_id': acc.id,
                'name': ref,
                'debit': resid if resid > 0 else 0.0,
                'credit': -resid if resid < 0 else 0.0,
            }))
            net += resid
        lines.append((0, 0, {
            'account_id': offset.id,
            'name': ref,
            'debit': -net if net < 0 else 0.0,
            'credit': net if net > 0 else 0.0,
        }))
        return _post_move(env, key, {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': OPENING_DATE,
            'ref': ref,
            'line_ids': lines,
            '_amount': net,
        }, stats), net

    total = 0.0
    made = 0
    for partner_id, items in grouped.items():
        partner = _partner(env, partner_id)
        if not partner:
            common.log("คำเตือน: ไม่พบคู่ค้า OD19 สำหรับ id เดิม %s (entry residual)"
                       % partner_id)
            stats.error += 1
            continue
        ref = 'ยอดค้างจากรายการบัญชีเดิม (entry) ณ %s - %s' % (
            OPENING_DATE, partner.display_name)
        _rec, net = _emit('%s.%s' % (ENTRY_TAG, partner_id), items, ref)
        total += net
        made += 1

    if no_partner:
        ref = 'ยอดค้างจากรายการบัญชีเดิม (entry) ไม่ระบุคู่ค้า ณ %s' % OPENING_DATE
        _rec, net = _emit('%s.nopartner' % ENTRY_TAG, no_partner, ref)
        total += net
        made += 1

    common.log("JE residual (entry): %d ใบ (partner=%d + nopartner=%d) | ยอดสุทธิ=%.2f"
               % (made, len(grouped), 1 if no_partner else 0, total))


# --------------------------------------------------------------------------
# (4) Gate — ตรวจยอด AR/AP รวม
# --------------------------------------------------------------------------
def _balance(env, account_type):
    lines = env['account.move.line'].search([
        ('parent_state', '=', 'posted'),
        ('date', '<=', OPENING_DATE),
        ('account_id.account_type', '=', account_type),
    ])
    return round(sum(lines.mapped('balance')), 2)


def _verify(env, stats):
    ar = _balance(env, 'asset_receivable')
    ap = _balance(env, 'liability_payable')
    d_ar = round(ar - TARGET_AR, 2)
    d_ap = round(ap - TARGET_AP, 2)
    if common.DRY_RUN:
        common.log("[DRY-RUN] ยอด AR/AP ที่วัดได้ (ก่อนเขียน) : AR=%.2f AP=%.2f" % (ar, ap))
        return
    common.log("GATE AR: %.2f (เป้า %.2f, ต่าง %.2f)" % (ar, TARGET_AR, d_ar))
    common.log("GATE AP: %.2f (เป้า %.2f, ต่าง %.2f)" % (ap, TARGET_AP, d_ap))
    if abs(d_ar) >= 0.01 or abs(d_ap) >= 0.01:
        raise ValueError(
            "ยอด AR/AP ไม่ตรงเป้า: AR diff=%.2f, AP diff=%.2f" % (d_ar, d_ap))
    common.log("GATE ผ่าน: AR/AP ตรงเป้า ณ %s" % OPENING_DATE)


def run(stats):
    env = common.odoo_env()
    _purge_duplicates(env, stats)
    _create_real_docs(env, stats)
    _create_entry_residual(env, stats)
    _verify(env, stats)
