# -*- coding: utf-8 -*-
"""ย้ายการอ้างอิงบัญชีชุดที่ 3 (บัญชี 6 หลักชุดสุดท้าย + PP36 input VAT) — COA Cleanup (odoo19_puat)

ที่มา: หลัง Remap รอบ 1 (21 บัญชี) และรอบ 2 (8 บัญชี) + Archive 4 บัญชี placeholder
       บัญชี 6 หลักมาตรฐาน l10n_th ที่ยัง active เหลือ 7 ตัว — 999999 (Current Year
       Earnings) เก็บไว้ (เป็นบัญชีมาตรฐาน Odoo, 125 move lines) จึงเหลือ 6 ตัวที่ต้องจัดการ
       + บัญชี 114200 (PP36 input VAT) ที่ถูก archive แล้วแต่ยังถูกอ้างโดย tax repartition
       (per คำยืนยันปลายทางจากผู้ใช้ 2026-11-06)

หลักการ (เหมือน remap_accounts.py / remap_accounts_round2.py):
    * เขียนข้อมูลผ่าน ORM เท่านั้น (ไม่ใช้ SQL ตรงสำหรับการเขียน)
    * ค่าเริ่มต้นเป็น DRY-RUN (อ่านอย่างเดียว) — ต้องตั้ง OD19_REMAP_CONFIRM=1 จึงเขียนจริง
    * แตะเฉพาะ "ค่าตั้งต้น/config" 3 กลุ่ม:
        1) ฟิลด์ Many2one ปกติที่ชี้มาที่บัญชีเดิม (journal default/suspense, res.company,
           account.reconcile.model.line, account.tax.repartition.line)
        2) ฟิลด์ company_dependent (jsonb) ที่เก็บบัญชีเดิมไว้จริง
        3) ir.default (ค่าตั้งต้นระบบ)
      ไม่แตะรายการบัญชีที่ลงไว้แล้ว (account.move.line) — ถ้าพบจะรายงานและข้าม
    * บัญชีเดิมไม่ถูกลบ — หลัง remap สำเร็จจะตั้งสถานะ Archive (active=False)

ตารางจับคู่ (final — ผู้ใช้ยืนยันแล้ว):
    111201  Bank Suspense Account  -> 1116.00   เงินโอนระหว่างบัญชี   (company suspense + 14 journals suspense)
    111202  Liquidity Transfer     -> 1116.00   เงินโอนระหว่างบัญชี   (company transfer + reconcile model)
    111203  Bank (BNK1 default)    -> 1112.00   เงินฝากกระแสรายวัน     (journal BNK1 default)
    111206  Cash(เงินสดย่อย) (CA)  -> 1111.01   เงินสดย่อย            (journal CA #4110 default)
    213200  Output VAT             -> 2211.01   ภาษีขาย               (8 tax repartition lines)
    114200  Input VAT (PP36)       -> 1151.01   ภาษีซื้อ              (2 tax repartition lines ของ PP36)
    111200  Bank Deposits          -> (archive) ไม่มีการอ้างอิง เก็บได้เลย

หมายเหตุสำคัญ (ต้องทำคู่กัน):
    บัญชี 213200/114200 ถูก hardcode ไว้ในโมดูล custom_addons/od19_thai_tax_reports
    (models/account_tax.py: OD19_PP36_OUTPUT_VAT / OD19_PP36_INPUT_VAT) และมี
    <function> ใน data file ที่รันตอน install/upgrade — หากไม่แก้โมดูลให้ค้นด้วยรหัส
    ใหม่ การ upgrade จะ set ค่ากลับเป็น 213200/114200 ทุกครั้ง

วิธีใช้ (รันจาก root ของโปรเจกต์ c:\\odoo-dev\\odoo19):

    # 1) ดูผลที่จะเกิดขึ้น (ไม่เขียนจริง)
    Get-Content -Raw migration\\cleanup\\remap_accounts_round3.py |
        venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http

    # 2) เขียนจริง (ต้องยืนยัน)
    $env:OD19_REMAP_CONFIRM = "1"
    Get-Content -Raw migration\\cleanup\\remap_accounts_round3.py |
        venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http
    Remove-Item Env:\\OD19_REMAP_CONFIRM

ตัวแปรสภาพแวดล้อม:
    OD19_REMAP_CONFIRM=1   ยืนยันการเขียนจริง (ถ้าไม่ตั้ง = DRY-RUN)
"""
import os
import json

CONFIRM = os.environ.get('OD19_REMAP_CONFIRM', '') == '1'
DRY_RUN = not CONFIRM

# ---------------------------------------------------------------------------
# 1) ตารางจับคู่บัญชีเดิม -> บัญชีปลายทาง (ชุดที่ 3)
# ---------------------------------------------------------------------------
MAP = {
    "111201": "1116.00",
    "111202": "1116.00",
    "111203": "1112.00",
    "111206": "1111.01",
    "213200": "2211.01",
    "114200": "1151.01",
}

# บัญชีที่ไม่มีการอ้างอิงคงเหลือ — archive อย่างเดียว
ARCHIVE_ONLY = ["111200"]

# บัญชีปลายทางที่ต้องสร้างใหม่ (รอบนี้ไม่มี — บัญชีปลายทางมีอยู่ครบแล้ว)
NEW_ACCOUNTS = {}

# Archive บัญชีเดิมหลัง remap สำเร็จ (ลบไม่ได้เพราะติด constraint)
ARCHIVE_SOURCES = True

# โมเดลธุรกรรม (posted entries) — ห้าม remap อัตโนมัติ ถ้าพบให้รายงานและข้าม
#   account.move.tax.invoice : account_id เป็น related(stored) ของ move_line_id.account_id
#                              (ผูกกับ posted move) — ถ้า remap ตรงจะขัดกับ move line และถูก
#                              recompute ทับ จึงต้องข้าม
TRANSACTIONAL_MODELS = {
    'account.move', 'account.move.line', 'account.payment',
    'account.bank.statement.line', 'account.partial.reconcile',
    'account.full.reconcile', 'account.analytic.line', 'account.analytic.account',
    'account.move.tax.invoice',
}

_FIELDS_CACHE = None


def log(msg):
    print("REMAP3| %s" % msg, flush=True)


def account_by_code(env, code, active_test=True):
    """ค้นบัญชีตามรหัส (ค่าเริ่มต้นรวมบัญชีที่ archive แล้ว)."""
    Acct = env['account.account'].sudo().with_context(active_test=active_test)
    return Acct.search([('code', '=', code)], limit=1)


def candidate_fields(env):
    """รายชื่อฟิลด์ FK ที่ชี้มาที่ account.account (stored many2one) — cache ไว้ใช้ซ้ำ."""
    global _FIELDS_CACHE
    if _FIELDS_CACHE is None:
        rows = env['ir.model.fields'].sudo().search_read(
            [('ttype', '=', 'many2one'),
             ('relation', '=', 'account.account'),
             ('store', '=', True)],
            ['model', 'name', 'company_dependent'])
        # ข้ามโมเดลที่เป็น SQL view (_auto=False เช่น account.account.reconcile,
        # mis.cash_flow) — เขียนไม่ได้ (ไม่มีตารางจริง)
        _FIELDS_CACHE = [r for r in rows
                         if r['model'] in env
                         and getattr(env[r['model']], '_auto', True)]
    return _FIELDS_CACHE


def scan_references(env, old_codes):
    """สแกนหาการอ้างอิงบัญชีเดิมทั้ง 3 กลุ่ม — คืนรายการ hit (ยังไม่แก้อะไร).

    กลุ่มที่ 1: ฟิลด์ Many2one ปกติ (ผ่าน ORM search)
    กลุ่มที่ 2: ฟิลด์ company_dependent (jsonb) — อ่านค่าที่เก็บจริงด้วย SQL
    กลุ่มที่ 3: ir.default (ค่าตั้งต้นระบบ) — อ่านด้วย SQL
    """
    old_ids = list(old_codes)          # [account_id, ...]
    id_to_code = dict(old_codes)       # {account_id: code}
    fields = candidate_fields(env)
    hits = []

    # --- กลุ่มที่ 1: ฟิลด์ปกติ (ไม่ company_dependent) -----------------------
    scanned = 0
    for f in fields:
        if f['company_dependent']:
            continue
        model, fname = f['model'], f['name']
        Model = env[model].sudo()
        try:
            recs = Model.with_context(active_test=False).search_read(
                [(fname, 'in', old_ids)], ['id', fname])
            scanned += 1
            _collect(hits, 'field', model, fname, False, recs, id_to_code, None)
        except Exception:
            continue

    # --- กลุ่มที่ 2: company_dependent (jsonb) -------------------------------
    jsonb_hits = _scan_jsonb(env, fields, id_to_code)

    # --- กลุ่มที่ 3: ir.default ---------------------------------------------
    default_hits = _scan_ir_default(env, id_to_code)

    hits += jsonb_hits + default_hits
    log("สแกน: ฟิลด์ปกติ %d ครั้ง | jsonb(จริง) %d จุด | ir.default %d จุด → รวม %d จุด" % (
        scanned, len(jsonb_hits), len(default_hits), len(hits)))
    return hits


def _collect(hits, kind, model, fname, company_dependent, recs, id_to_code, company_id):
    """จัดกลุ่มผลลัพธ์ ORM เป็นรายการ hit (ต่อ 1 โมเดล/ฟิลด์/บัญชีเดิม)."""
    grouped = {}
    for r in recs:
        val = r.get(fname)
        if not val:
            continue
        target_id = val[0] if isinstance(val, (list, tuple)) else val
        grouped.setdefault(target_id, []).append(r['id'])
    for target_id, ids in grouped.items():
        hits.append({
            'kind': kind,
            'model': model,
            'field': fname,
            'company_dependent': company_dependent,
            'company_id': company_id,
            'old_id': target_id,
            'old_code': id_to_code.get(target_id, str(target_id)),
            'ids': ids,
        })


def _scan_jsonb(env, fields, id_to_code):
    """สแกนฟิลด์ company_dependent (jsonb) — นับเฉพาะค่าที่ "เก็บจริง" เท่านั้น."""
    old_ids = set(id_to_code)
    hits = []
    for f in fields:
        if not f['company_dependent']:
            continue
        model, fname = f['model'], f['name']
        if model not in env:
            continue
        table = env[model]._table
        try:
            env.cr.execute(
                'SELECT id, "%s" FROM "%s" WHERE "%s" IS NOT NULL' % (fname, table, fname))
            data = env.cr.fetchall()
        except Exception:
            continue
        grouped = {}
        for rid, val in data:
            if not isinstance(val, dict):
                continue
            for comp, v in val.items():
                if isinstance(v, int) and v in old_ids:
                    grouped.setdefault((int(comp), v), []).append(rid)
        for (comp, v), ids in grouped.items():
            hits.append({
                'kind': 'jsonb',
                'model': model,
                'field': fname,
                'company_dependent': True,
                'company_id': comp,
                'old_id': v,
                'old_code': id_to_code[v],
                'ids': ids,
            })
    return hits


def _scan_ir_default(env, id_to_code):
    """สแกน ir.default — เฉพาะฟิลด์ที่ relation = account.account."""
    old_ids = set(id_to_code)
    hits = []
    env.cr.execute("SELECT id, field_id, company_id, json_value FROM ir_default")
    rows = env.cr.fetchall()
    for rid, fid, comp, jval in rows:
        if not fid:
            continue
        fld = env['ir.model.fields'].browse(fid)
        if fld.relation != 'account.account':
            continue
        try:
            val = json.loads(jval) if isinstance(jval, str) else jval
        except Exception:
            continue
        vals = val if isinstance(val, list) else [val]
        for one in vals:
            if isinstance(one, int) and one in old_ids:
                hits.append({
                    'kind': 'ir.default',
                    'model': fld.model,
                    'field': fld.name,
                    'company_dependent': False,
                    'company_id': comp,
                    'old_id': one,
                    'old_code': id_to_code[one],
                    'ids': [rid],
                })
    return hits


def _describe(h):
    """ข้อความอธิบาย hit 1 รายการ (ใช้ใน log) — ย่อรายการ id ที่ยาวเกิน 8 ตัว."""
    comp = (" company=%d" % h['company_id']) if h['company_id'] else ""
    ids = h['ids']
    ids_txt = str(ids) if len(ids) <= 8 else "%s … +%d" % (ids[:8], len(ids) - 8)
    return "%s → %s | [%s] %s.%s%s | %d รายการ | ids=%s" % (
        h['old_code'], MAP.get(h['old_code'], '?'), h['kind'],
        h['model'], h['field'], comp, len(ids), ids_txt)


def _apply_hit(env, h, new_id):
    """เขียนค่าใหม่ตามชนิดของ hit."""
    if h['kind'] == 'ir.default':
        env['ir.default'].set(h['model'], h['field'], new_id,
                              company_id=h['company_id'])
    elif h['kind'] == 'jsonb':
        env[h['model']].sudo().browse(h['ids']).with_company(
            h['company_id']).write({h['field']: new_id})
    else:  # ฟิลด์ปกติ
        env[h['model']].sudo().browse(h['ids']).with_context(
            active_test=False).write({h['field']: new_id})


def main():
    env = globals()['env']  # noqa: F821 — ตัวแปร env มีให้โดย odoo shell
    dbname = env.cr.dbname
    log("ฐานข้อมูล: %s | โหมด: %s" % (dbname, "DRY-RUN (อ่านอย่างเดียว)" if DRY_RUN else "WRITE (เขียนจริง)"))

    # --- 1) หาบัญชีเดิมทุกตัว (ทั้ง remap และ archive-only) -------------------
    old_accounts = {}   # {account_id: code}  — เฉพาะที่ต้อง remap
    archive_accounts = {}  # {account_id: code} — ทั้งหมดที่จะ archive
    for old_code in list(MAP.keys()) + ARCHIVE_ONLY:
        acct = account_by_code(env, old_code, active_test=False)
        if not acct:
            log("!! ไม่พบบัญชีเดิม %s — ข้าม" % old_code)
            continue
        archive_accounts[acct.id] = old_code
        if old_code in MAP:
            old_accounts[acct.id] = old_code
    log("พบบัญชีเดิมที่จะ remap: %d/%d | จะ archive ทั้งหมด: %d/%d" % (
        len(old_accounts), len(MAP), len(archive_accounts), len(MAP) + len(ARCHIVE_ONLY)))

    # ตรวจว่าบัญชีปลายทางมีจริงครบ
    for old_code, new_code in MAP.items():
        if not account_by_code(env, new_code, active_test=True):
            log("!! ไม่พบบัญชีปลายทาง %s (สำหรับ %s)" % (new_code, old_code))

    # --- 2) สแกนการอ้างอิง ---------------------------------------------------
    hits = scan_references(env, old_accounts)

    # --- 3) รายงานผลที่จะทำ --------------------------------------------------
    ok_hits = [h for h in hits if h['model'] not in TRANSACTIONAL_MODELS]
    tx_hits = [h for h in hits if h['model'] in TRANSACTIONAL_MODELS]
    log("จุดอ้างอิง config ที่จะย้าย: %d จุด | ธุรกรรม (ข้าม): %d จุด" % (len(ok_hits), len(tx_hits)))
    for h in sorted(hits, key=lambda x: (x['old_code'], x['kind'], x['model'])):
        tag = " [ธุรกรรม-ข้าม]" if h['model'] in TRANSACTIONAL_MODELS else ""
        log("  %s%s" % (_describe(h), tag))
    if not hits:
        log("  (ไม่พบการอ้างอิงคงเหลือ)")

    remaining = sorted({h['old_code'] for h in ok_hits})
    log("บัญชีเดิมที่ยังมีจุดอ้างอิง (config): %s" % (", ".join(remaining) if remaining else "—"))

    if DRY_RUN:
        if ARCHIVE_SOURCES:
            log("จะ archive บัญชีเดิมทั้ง %d ตัว (active=False) หลัง remap สำเร็จ" % len(archive_accounts))
        log("DRY-RUN เสร็จ — ยังไม่แก้ข้อมูล (ตั้ง OD19_REMAP_CONFIRM=1 เพื่อเขียนจริง)")
        return

    # --- 4) remap จริง -------------------------------------------------------
    done_fields = 0
    for h in ok_hits:
        new_rec = account_by_code(env, MAP[h['old_code']], active_test=True)
        try:
            with env.cr.savepoint():
                _apply_hit(env, h, new_rec.id)
            done_fields += 1
        except Exception as exc:
            lines = str(exc).strip().splitlines()
            log("!! ย้ายไม่สำเร็จ %s.%s → %s: %s" % (
                h['model'], h['field'], MAP[h['old_code']], (lines[0] if lines else exc)[:180]))
    env.cr.commit()
    log("remap สำเร็จ %d/%d จุด" % (done_fields, len(ok_hits)))

    # --- 5) Archive บัญชีเดิมทั้งหมด -----------------------------------------
    if ARCHIVE_SOURCES:
        archived = 0
        for acct_id, old_code in sorted(archive_accounts.items()):
            acct = env['account.account'].sudo().browse(acct_id).exists()
            if not acct:
                continue
            try:
                with env.cr.savepoint():
                    acct.write({'active': False})
                archived += 1
                log("archive บัญชีเดิม %s (id=%d)" % (old_code, acct_id))
            except Exception as exc:
                lines = str(exc).strip().splitlines()
                log("!! archive ไม่สำเร็จ %s: %s" % (old_code, (lines[0] if lines else exc)[:180]))
        env.cr.commit()
        log("archive บัญชีเดิมสำเร็จ %d/%d" % (archived, len(archive_accounts)))

    # --- 6) ตรวจสอบหลังทำ ----------------------------------------------------
    left = scan_references(env, old_accounts)
    left_ok = [h for h in left if h['model'] not in TRANSACTIONAL_MODELS]
    log("หลัง remap — จุดอ้างอิง config คงเหลือ: %d จุด" % len(left_ok))
    for h in left_ok:
        log("  คงเหลือ: %s" % _describe(h))
    still_active = [c for c in list(MAP.keys()) + ARCHIVE_ONLY
                    if account_by_code(env, c, active_test=True)]
    log("บัญชีเดิมที่ยัง active: %s" % (", ".join(still_active) if still_active else "— (ครบทุกตัว)"))
    log("เสร็จสิ้น (CONFIRM=1)")


main()
