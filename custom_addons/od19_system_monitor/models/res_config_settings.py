# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ค่าตั้งของระบบเฝ้าระวังสุขภาพ Odoo 19 (P3/P4/P5).

ผูกฟิลด์กับ ``ir.config_parameter`` ผ่าน ``config_parameter`` โดยใช้คีย์ชุดเดียว
กับที่ cron, endpoint และ hook อ่านจริง (ประกาศไว้ใน ``od19_health_common``)
เพื่อให้ค่าที่ผู้ใช้ตั้งในหน้าตั้งค่ามีผลทันทีโดยไม่ต้องมีที่เก็บที่สอง
"""

from odoo import fields, models

from .od19_health_common import (
    DEFAULT_DIGEST_HOUR,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_RETENTION_DAYS,
    PARAM_AI_TRIAGE_ENABLED,
    PARAM_DATA_DIR,
    PARAM_DIGEST_ENABLED,
    PARAM_DIGEST_HOUR,
    PARAM_ENABLED,
    PARAM_HEARTBEAT_TOKEN,
    PARAM_LOG_BACKUP_COUNT,
    PARAM_LOG_MAX_BYTES,
    PARAM_LOG_ROTATION_ENABLED,
    PARAM_RETENTION_DAYS,
)


class ResConfigSettings(models.TransientModel):
    """ค่าตั้งต้นของระบบเฝ้าระวังสุขภาพ (หมวด System Health Monitor)."""

    _inherit = "res.config.settings"

    od19_health_enabled = fields.Boolean(
        string="เปิดใช้การเฝ้าระวังสุขภาพระบบ",
        config_parameter=PARAM_ENABLED,
        default=True,
        help="ปิดชั่วคราวได้เมื่อต้องการหยุดการตรวจทั้งหมด (cron จะไม่บันทึกผล).",
    )
    od19_health_retention_days = fields.Integer(
        string="เก็บผลการตรวจย้อนหลัง (วัน)",
        config_parameter=PARAM_RETENTION_DAYS,
        default=DEFAULT_RETENTION_DAYS,
    )
    od19_health_digest_enabled = fields.Boolean(
        string="ส่งสรุปสุขภาพประจำวัน",
        config_parameter=PARAM_DIGEST_ENABLED,
        default=True,
    )
    od19_health_digest_hour = fields.Integer(
        string="เวลาส่งสรุป (ชั่วโมง 0-23)",
        config_parameter=PARAM_DIGEST_HOUR,
        default=DEFAULT_DIGEST_HOUR,
    )
    od19_health_ai_triage_enabled = fields.Boolean(
        string="เปิดใช้การวินิจฉัยด้วย AI (โหมดอ่านอย่างเดียว)",
        config_parameter=PARAM_AI_TRIAGE_ENABLED,
        default=False,
        help="โหมด A: AI อ่านข้อมูลเหตุการณ์เพื่อสรุปสาเหตุเท่านั้น "
        "ห้ามสั่งแก้ไขระบบ อนุมัติ หรือชำระเงิน.",
    )
    od19_health_heartbeat_token = fields.Char(
        string="โทเคนรับสัญญาณชีพ",
        config_parameter=PARAM_HEARTBEAT_TOKEN,
        help="ค่าที่สคริปต์ภายนอกต้องส่งมาที่ส่วนหัว X-Health-Token "
        "เมื่อเรียก POST /od19/health/heartbeat.",
    )
    od19_health_data_dir = fields.Char(
        string="โฟลเดอร์ข้อมูล (data-dir)",
        config_parameter=PARAM_DATA_DIR,
        help="ใช้คำนวณขนาด filestore เมื่อไม่ได้ตั้งค่าใน odoo.conf.",
    )

    # --- P4: สุขอนามัยของ log (ต้องรีสตาร์ท Odoo หลังเปลี่ยนค่า) ---
    od19_health_log_rotation_enabled = fields.Boolean(
        string="หมุนไฟล์ log ขณะรัน",
        config_parameter=PARAM_LOG_ROTATION_ENABLED,
        default=True,
        help="ติดตั้ง log handler แบบหมุนไฟล์จากฝั่ง custom โดยไม่แก้โค้ด core "
        "(มีผลหลังรีสตาร์ท Odoo).",
    )
    od19_health_log_max_bytes = fields.Integer(
        string="ขนาดไฟล์ log สูงสุด (ไบต์)",
        config_parameter=PARAM_LOG_MAX_BYTES,
        default=DEFAULT_LOG_MAX_BYTES,
    )
    od19_health_log_backup_count = fields.Integer(
        string="จำนวนไฟล์ log ที่เก็บย้อนหลัง",
        config_parameter=PARAM_LOG_BACKUP_COUNT,
        default=DEFAULT_LOG_BACKUP_COUNT,
    )
