# -*- coding: utf-8 -*-
"""s02_master — ข้อมูลหลัก: สมุดรายวัน / ภาษี / เงื่อนไขชำระ / ราคา"""
import common


def run(stats):
    common.log("s02_master: (scaffold) — ยังไม่ได้นำเข้าจริง")

    # TODO(สมุดรายวัน - journal_map.csv): เทียบ account.journal ของเดิมกับใหม่ด้วย 'code'
    #   ปรับชื่อ/ชนิด (sale/purchase/cash/bank)/บัญชีเริ่มต้น ให้ตรงกับระบบเดิม
    #   env['account.journal'].search([('code', '=', '...')]).write({...})
    #
    # TODO(ภาษี - tax_map.csv): ดูรายละเอียดใน s01_reference แล้วปรับอัตรา/บัญชีให้ตรง
    #   (ชนิดขาย/ซื้อ, อัตรา, บัญชีใน repartition line)
    #
    # TODO(เงื่อนไขชำระ - payment_term_map.csv): สร้าง account.payment.term ให้ครบ
    #   พร้อม account.payment.term.line (เปอร์เซ็นต์/จำนวนวัน เช่น 30/60/90 วัน)
    #
    # TODO(ราคา/นโยบายราคา - pricelist): นำเข้า product.pricelist และ
    #   product.pricelist.item (ค่าเริ่มต้น/ช่วงจำนวน/เปอร์เซ็นต์ส่วนลด)
    #   โดยแนบ External ID ให้ทุกใบผ่าน common.upsert
    #
    # TODO(หน่วยนับ - uom_map.csv): เทียบ uom.uom (ก่อน v17 คือ product.uom) ให้ตรงกัน
    #   ป้องกันปัญหาสูตรแปลงหน่วย (ratio) เพี้ยน
    stats.skipped += 1
