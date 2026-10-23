# -*- coding: utf-8 -*-
"""s01_reference — นำเข้าข้อมูลอ้างอิง: บริษัท / สกุลเงิน / ผังบัญชี / ภาษี"""
import common


def run(stats):
    common.log("s01_reference: ตรวจสอบความถูกต้องของผังบัญชี (account_map.csv)")
    _validate_account_map(stats)

    # ------------------------------------------------------------------
    # TODO(บริษัท): อัปเดตข้อมูลบริษัทหลักให้ตรงกับระบบเดิม
    #   เช่น env.company.partner_id.write({'name': ..., 'vat': ...,
    #       'street': ..., 'city': ..., 'zip': ...})
    #   รวมถึงตั้งค่าชื่อภาษี (tax_name) และรหัสสาขา (branch_code) ถ้าโมดูล
    #   od19_partner_thai_fields ถูกติดตั้งแล้ว
    #
    # TODO(สกุลเงิน): ตรวจว่าสกุลเงินที่ระบบเดิมใช้ (THB/USD/...) เปิดใช้งานครบ
    #   env['res.currency'].search([('name', 'in', [...])]).write({'active': True})
    #   และนำเข้าอัตราแลกเปลี่ยนเริ่มต้นผ่าน res.currency.rate ถ้าจำเป็น
    #   (ระวัง: อัตราแลกเปลี่ยนต้องอิงวันที่และบริษัทให้ถูกต้อง)
    #
    # TODO(ผังบัญชี): กรณีรหัสบัญชีที่ต้องมีใหม่ใน Odoo 19 ให้สร้าง account.account
    #   โดยต้องระบุ account_type ให้ถูกต้อง (asset/liability/income/expense)
    #   ข้อมูลรหัสและชื่อบัญชีมาจากไฟล์ mapping/account_map.csv
    #
    # TODO(ภาษี): เทียบภาษีระบบเดิมกับระบบใหม่ด้วย tax_map.csv แล้วสร้าง/แก้ไข
    #   account.tax ให้ตรงชนิด (ขาย/ซื้อ), อัตรา, และบัญชีที่เกี่ยวข้อง
    #   (ตรวจฟิลด์ type_tax_use และ invoice_repartition_line_ids)
    # ------------------------------------------------------------------


def _validate_account_map(stats):
    """ตรวจว่าไฟล์ account_map.csv ใช้ได้จริงกับ Odoo 19 (ทำงานได้จริงตามที่ออกแบบ)."""
    mapping = common.load_map('account_map.csv')
    if not mapping:
        common.log("คำเตือน: account_map.csv ยังไม่มีแถวข้อมูลจริง (เหลือแต่แถวตัวอย่าง EXAMPLE)")
        return

    env = common.odoo_env()
    Account = env['account.account']
    wanted_codes = sorted({row.get('od19_code') for row in mapping.values() if row.get('od19_code')})
    found_codes = set(Account.search([('code', 'in', wanted_codes)]).mapped('code'))

    for legacy_code, row in mapping.items():
        od19_code = row.get('od19_code')
        if not od19_code:
            common.log("ผิดพลาด: แถว mapping ของ legacy '%s' ไม่มี od19_code (note=%s)"
                       % (legacy_code, row.get('note')))
            stats.error += 1
            continue
        if od19_code not in found_codes:
            common.log("ผิดพลาด: ไม่พบบัญชี Odoo 19 รหัส '%s' (legacy %s, note=%s)"
                       % (od19_code, legacy_code, row.get('note')))
            stats.error += 1

    # ตรวจรหัสบัญชีฝั่งระบบเดิมที่ยังไม่ได้ทำ mapping
    for legacy_code in _legacy_account_codes():
        if legacy_code not in mapping:
            common.log("ผิดพลาด: รหัสบัญชีในระบบเดิม '%s' ยังไม่มีใน account_map.csv" % legacy_code)
            stats.error += 1

    common.log("s01_reference: ตรวจสอบผังบัญชีเสร็จ (ตรวจทั้งหมด %d แถว)" % len(mapping))


def _legacy_account_codes():
    """อ่านรหัสบัญชีทั้งหมดจากระบบเดิม (อ่านอย่างเดียว).

    หมายเหตุ: ใน Odoo 15 ฟิลด์ code ของ account_account เป็นแบบ company-dependent
    อาจต้องปรับ SQL ให้ตรงกับโครงสร้างจริง (เช่น code_store) ก่อนใช้งาน
    """
    try:
        import legacy
        rows = legacy.fetch_all("SELECT code FROM account_account")
    except Exception as exc:
        common.log("คำเตือน: อ่านผังบัญชีจากระบบเดิมไม่ได้ (%s) — ข้ามการตรวจ unmapped" % exc)
        return []
    return [r['code'] for r in rows if r.get('code')]
