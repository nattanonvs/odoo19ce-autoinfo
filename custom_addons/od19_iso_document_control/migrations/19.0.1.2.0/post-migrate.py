# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

"""อัปเดตข้อมูลเดิมของหมวดเอกสาร ISO (noupdate=1 จึงแก้ผ่าน XML ไม่มีผล).

- เปลี่ยนหมวด PROC -> PM (Procedure Manual)
- ปิด "ใช้เลขคุม" ให้ REC / MANUAL / POL (ยังมีไว้ได้ แต่ไม่สร้างรหัสอัตโนมัติ)
- ลบ ir.sequence เดิมของ PROC (ถูกแทนที่ด้วย seq_iso_doc_pm)
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # 1) PROC -> PM (Procedure Manual)
    cr.execute(
        """
        UPDATE od19_iso_document_category
           SET prefix = 'PM',
               name = 'ขั้นตอนการปฏิบัติงาน (Procedure Manual)'
         WHERE prefix = 'PROC'
        """
    )
    if cr.rowcount:
        _logger.info("ISO Document Control: renamed %s category(ies) PROC -> PM", cr.rowcount)

    # 2) ปิดเลขคุมให้ บันทึก / คู่มือระบบ / นโยบาย
    cr.execute(
        """
        UPDATE od19_iso_document_category
           SET use_sequence = FALSE
         WHERE prefix IN ('REC', 'MANUAL', 'POL')
        """
    )
    if cr.rowcount:
        _logger.info(
            "ISO Document Control: disabled controlled numbering for %s category(ies)",
            cr.rowcount,
        )

    # 3) ลบ sequence เดิมของ PROC ที่ไม่ใช้แล้ว
    cr.execute(
        "DELETE FROM ir_model_data "
        " WHERE module = 'od19_iso_document_control' AND name = 'seq_iso_doc_proc'"
    )
    cr.execute("DELETE FROM ir_sequence WHERE code = 'od19.iso.document.proc'")
