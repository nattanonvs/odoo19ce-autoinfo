# -*- coding: utf-8 -*-
"""s08_opening — ยอดยกมา: AR/AP, สินค้าคงเหลือ, สินทรัพย์, WHT/เบิกล่วงหน้า/เช็ค

ข้อควรระวังที่สุดของขั้นตอนนี้:
    ยอดยกมาคือ "จุดตั้งต้น" ของบัญชีจริง ต้องกระทบยอดกับงบการเงินของระบบเดิม
    ให้ตรงก่อนนำเข้า (AR/AP/สินค้าคงเหลือ/สินทรัพย์) ห้ามรันจริงโดยไม่ตรวจยอด
"""
import common


def run(stats):
    common.log("s08_opening: (scaffold) — ต้องตรวจสอบยอดกับงบการเงินก่อนใช้จริง")
    _todo_ar_ap()
    _todo_stock()
    _todo_assets()
    _todo_wht_advance_cheque()
    # เมื่อพัฒนาเสร็จให้เปลี่ยนจากการนับ skipped เป็นการ upsert จริงพร้อม External ID
    stats.skipped += 1


def _todo_ar_ap():
    """(a) ยอดยกมาลูกหนี้/เจ้าหนี้ (AR/AP)."""
    # ใช้ account.move ชนิด move_type='entry'
    # ตรวจสอบแล้ว: 'entry' มีอยู่ใน selection ของ account.move.move_type
    #   -> c:\\odoo-dev\\odoo19\\addons\\account\\models\\account_move.py:145
    #
    # หลักการ:
    #   * สร้าง 1 ใบต่อคู่ค้า (หรือใบรวม แต่ต้องมีบรรทัดแยก partner_id ครบ)
    #   * ตั้ง partner_id บน account.move.line ทุกบรรทัด เพื่อให้รายงานอายุลูกหนี้ (aging) ทำงาน
    #   * ลงบัญชีคู่กับ "บัญชีลูกหนี้/เจ้าหนี้" และ "บัญชียอดยกมาคู่ปรับ" ให้ balance = 0
    #   * ใช้ move.action_post() เพื่อยืนยันรายการ
    #   * ผูก External ID เพื่อกันข้อมูลซ้ำเมื่อรันซ้ำ
    #     (common.upsert สร้างได้ระดับ record เดียว จึงควรมีฟังก์ชัน upsert_move()
    #      เฉพาะกิจ เพราะต้องประกอบ line_ids เอง)
    #
    # ตัวอย่าง (ร่าง):
    #   move = env['account.move'].create({
    #       'move_type': 'entry',
    #       'date': OPENING_DATE,
    #       'journal_id': opening_journal.id,
    #       'ref': 'ยอดยกมาลูกหนี้จากระบบเดิม',
    #       'line_ids': [
    #           (0, 0, {'account_id': ar_account.id, 'partner_id': pid,
    #                   'name': 'ยอดยกมา', 'debit': amount, 'credit': 0.0}),
    #           (0, 0, {'account_id': offset_account.id, 'debit': 0.0, 'credit': amount}),
    #       ],
    #   })
    #   move.action_post()
    pass


def _todo_stock():
    """(b) ยอดยกมาสินค้าคงเหลือ."""
    # แนวทางที่เลือก: stock.quant + _apply_inventory()
    # เหตุผล: โมเดล stock.inventory ถูกยกเลิกไปแล้วใน Odoo 19 จึงปรับยอดผ่าน stock.quant
    #   โดยตรง (ตรวจสอบแล้วว่าเหลือเฉพาะ wizard ไม่มีโมเดล stock.inventory)
    #   -> c:\\odoo-dev\\odoo19\\addons\\stock\\wizard\\stock_inventory_adjustment_name.py
    #   -> c:\\odoo-dev\\odoo19\\addons\\stock\\wizard\\stock_inventory_conflict.py
    #
    # ตรวจสอบชื่อเมธอดจริงแล้ว:
    #   stock.quant._apply_inventory(date=None)
    #     -> c:\\odoo-dev\\odoo19\\addons\\stock\\models\\stock_quant.py:996
    #   stock.quant.action_apply_inventory()
    #     -> c:\\odoo-dev\\odoo19\\addons\\stock\\models\\stock_quant.py:433
    #
    # ขั้นตอน:
    #   quant = env['stock.quant'].with_context(inventory_mode=True).create({
    #       'product_id': product_id,
    #       'location_id': stock_location_id,   # คลังหลักของบริษัท
    #       'inventory_quantity': qty,
    #   })
    #   quant._apply_inventory()   # สร้าง stock.move และทำให้เสร็จ -> เกิด stock.valuation.layer
    #
    # *** ข้อบังคับสำคัญ ***
    #   การยกมาสินค้าต้องสร้างชั้นมูลค่าสินค้า (stock.valuation.layer) ให้วิเคราะห์ต้นทุนต่อได้
    #   ต้องติดตั้งโมดูล od19_stock_fifo (c:\\odoo-dev\\odoo19\\custom_addons\\od19_stock_fifo)
    #   เพื่อให้ต้นทุนแบบ FIFO ต่อเนื่องจากยอดยกมา
    #   ห้ามเขียน stock.valuation.layer หรือยอดคงเหลือด้วย SQL ตรง ๆ เด็ดขาด
    pass


def _todo_assets():
    """(c) ยอดยกมาสินทรัพย์ถาวร."""
    # ใช้โมเดล account.asset
    # หมายเหตุ: account.asset มาจาก OCA account_asset_management
    #   -> ...\\third_party\\oca\\account-financial-tools\\account_asset_management\\models\\account_asset.py
    #   และถูกต่อเติมโดยโมดูล od19_asset_disposal (เพิ่ม state='disposed')
    #   -> c:\\odoo-dev\\odoo19\\custom_addons\\od19_asset_disposal\\models\\account_asset.py
    #
    # ต้องนำเข้าเป็นรายทรัพย์สิน: ชื่อ, มูลค่าตั้งต้น (original_value), วันได้มา (acquisition_date),
    #   โปรไฟล์ค่าเสื่อมราคา และตั้งค่าให้ยอดคงเหลือ (book value) ตรงกับระบบเดิม
    # *** ต้องตรวจสอบชื่อฟิลด์จริงในโมเดลก่อนเขียนโค้ด เพราะโมดูล OCA อาจต่างจาก core ***
    pass


def _todo_wht_advance_cheque():
    """(d) ภาษีหัก ณ ที่จ่าย / เงินเบิกล่วงหน้า / เช็ค."""
    # WHT (ภาษีหัก ณ ที่จ่าย):
    #   นำเข้ายอดค้างรับ/ค้างจ่ายผ่าน account.move ชนิด 'entry'
    #   โดยอ้างอิงบัญชี WHT ของระบบเดิม (map ผ่าน account_map.csv)
    #   รายงานที่เกี่ยวข้อง: od19_thai_tax_reports (wht_register)
    #
    # เงินเบิกล่วงหน้า:
    #   ใช้โมเดลของโมดูล od19_accounting_advance -> 'account.advance'
    #   c:\\odoo-dev\\odoo19\\custom_addons\\od19_accounting_advance\\models\\account_advance.py:6
    #
    # เช็ค:
    #   ใช้โมเดลของโมดูล od19_accounting_cheque
    #   -> 'account.cheque'      ...\\od19_accounting_cheque\\models\\account_cheque.py:7
    #   -> 'account.cheque.book' ...\\od19_accounting_cheque\\models\\account_cheque_book.py:8
    #
    # *** แนะนำ: นำเข้าเฉพาะ "ยอดยกมา" ที่ยังค้างอยู่ ไม่ต้องยกประวัติธุรกรรมเช็คทั้งหมด ***
    pass
