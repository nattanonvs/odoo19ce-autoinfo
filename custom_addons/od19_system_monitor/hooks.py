# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""P4 — สุขอนามัยของ log (ทำงานระดับ process ตอนโหลดโมดูล).

เรียกผ่านคีย์ ``post_load`` ใน ``__manifest__.py`` จึงทำงาน "ครั้งเดียวต่อ process"
(point นี้ Odoo เรียกก่อนที่โมเดลและข้อมูลจะถูกเตรียม — เหมาะกับการติดตั้ง
log handler ระดับ server-wide)

งานที่ทำ:
1. สลับไฟล์ log ของ Odoo ให้หมุนได้ขณะรัน — บน Windows Odoo เปิดไฟล์ log
   ค้างไว้ด้วย ``logging.FileHandler`` ธรรมดา (ดู ``odoo/netsvc.py``) จึงหมุน
   ตอนรันไม่ได้ เราแทนที่ด้วย ``RotatingFileHandler`` จากฝั่ง custom
   โดย **ไม่แก้โค้ด core** และไม่แตะ handler ที่หมุนอยู่แล้ว
2. กรอง warning เชิงสคีมาที่ไม่ actionable (เช่น ``Missing not-null constraint``)
   ออกจาก logger ``odoo.schema``
3. ติดแท็กโมดูล/เวอร์ชันให้ Sentry เฉพาะเมื่อติดตั้ง OCA sentry อยู่

ค่าควบคุมอ่านจาก ``ir.config_parameter`` ก่อน (ผ่านการเชื่อมต่อฐานข้อมูลแบบตรง
ไม่ต้องพึ่ง registry) แล้วจึงถอยไปอ่านจาก ``odoo.conf``
"""

import logging
import logging.handlers
import sys

from odoo import tools

from .models.od19_health_common import (
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_MAX_BYTES,
    PARAM_LOG_BACKUP_COUNT,
    PARAM_LOG_MAX_BYTES,
    PARAM_LOG_ROTATION_ENABLED,
)

_logger = logging.getLogger(__name__)

# ข้อความ warning เชิงสคีมาที่ไม่ actionable (กรองออกจาก logger odoo.schema)
_SCHEMA_NOISE = ("Missing not-null constraint",)


class _SchemaNoiseFilter(logging.Filter):
    """ปล่อยผ่านทุก record ยกเว้น warning เชิงสคีมาที่ไม่ actionable."""

    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 — อย่าให้ filter ทำให้ logging พัง
            return True
        return not any(marker in message for marker in _SCHEMA_NOISE)


def _database_name():
    """คืนชื่อฐานข้อมูลเป้าหมายจาก odoo.conf (หรือ None ถ้าไม่ได้ระบุ)."""
    value = tools.config.get("db_name")
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    if not value:
        return None
    return str(value).split(",")[0].strip() or None


def _db_param(key):
    """อ่านค่า ``key`` จาก ``ir.config_parameter`` โดยตรง (คืน None ถ้าอ่านไม่ได้).

    ใช้การเชื่อมต่อฐานข้อมูลแบบตรงเพื่อไม่ต้องพึ่ง registry ซึ่งยังไม่พร้อม
    ในจังหวะ post_load ถ้าตารางยังไม่มี (ติดตั้งครั้งแรก) จะคืน None แล้วถอยไปใช้
    ค่าจาก odoo.conf แทน
    """
    dbname = _database_name()
    if not dbname:
        return None
    try:
        from odoo.sql_db import db_connect

        with db_connect(dbname).cursor() as cr:
            cr.execute(
                "SELECT value FROM ir_config_parameter WHERE key = %s", (key,)
            )
            row = cr.fetchone()
            return row[0] if row else None
    except Exception:  # noqa: BLE001 — ต้องไม่ทำให้การโหลดโมดูลล้ม
        _logger.debug("อ่านค่ารวมศูนย์ %s ไม่ได้ — ถอยไปใช้ odoo.conf", key)
        return None


def _resolve(key, default=None):
    """หาค่าที่ใช้งานจริง: ir.config_parameter -> odoo.conf -> default."""
    value = _db_param(key)
    if value in (None, ""):
        value = tools.config.get(key)
    if value in (None, ""):
        return default
    return value


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _install_log_rotation():
    """สลับ ``FileHandler`` ของ root logger เป็น ``RotatingFileHandler``."""
    if not _as_bool(_resolve(PARAM_LOG_ROTATION_ENABLED, "True"), True):
        _logger.info("od19_system_monitor: ปิดการหมุนไฟล์ log ขณะรันไว้")
        return

    max_bytes = _as_int(_resolve(PARAM_LOG_MAX_BYTES), DEFAULT_LOG_MAX_BYTES)
    backup_count = _as_int(
        _resolve(PARAM_LOG_BACKUP_COUNT), DEFAULT_LOG_BACKUP_COUNT
    )
    if max_bytes <= 0 or backup_count <= 0:
        _logger.info(
            "od19_system_monitor: ข้ามการหมุน log เพราะค่า max_bytes/backup_count ไม่ถูกต้อง"
        )
        return

    root = logging.getLogger()
    replaced = 0
    for handler in list(root.handlers):
        if not isinstance(handler, logging.FileHandler):
            continue
        # ข้าม handler ที่หมุนเองอยู่แล้ว และ WatchedFileHandler (logrotate ภายนอก)
        if isinstance(
            handler,
            (logging.handlers.RotatingFileHandler, logging.handlers.WatchedFileHandler),
        ):
            continue
        filename = getattr(handler, "baseFilename", None)
        if not filename:
            continue
        rotating = logging.handlers.RotatingFileHandler(
            filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=getattr(handler, "encoding", None) or "utf-8",
        )
        rotating.setFormatter(handler.formatter)
        rotating.setLevel(handler.level)
        for flt in handler.filters:
            rotating.addFilter(flt)
        root.removeHandler(handler)
        handler.close()
        root.addHandler(rotating)
        replaced += 1

    if replaced:
        _logger.info(
            "od19_system_monitor: เปลี่ยน %s ไฟล์ log เป็นโหมดหมุนอัตโนมัติ "
            "(สูงสุด %s ไบต์, เก็บ %s ไฟล์)",
            replaced,
            max_bytes,
            backup_count,
        )
    else:
        _logger.debug(
            "od19_system_monitor: ไม่พบ FileHandler ที่ต้องสลับเป็นโหมดหมุน"
        )


def _apply_schema_filter():
    """ติดตัวกรอง warning เชิงสคีมาที่ไม่ actionable เข้ากับ logger odoo.schema."""
    logging.getLogger("odoo.schema").addFilter(_SchemaNoiseFilter())


def _extend_sentry():
    """ติดแท็กโมดูลให้ Sentry เฉพาะเมื่อติดตั้ง OCA sentry อยู่ (ไม่บังคับ)."""
    if "odoo.addons.sentry.hooks" not in sys.modules:
        return
    try:
        import sentry_sdk

        sentry_sdk.set_tag("od19.module", "od19_system_monitor")
    except Exception:  # noqa: BLE001 — Sentry ไม่พร้อมก็ข้ามได้
        _logger.debug("od19_system_monitor: ติดแท็ก Sentry ไม่สำเร็จ", exc_info=True)


def post_load():
    """จุดเข้าเดียวของ P4 — Odoo เรียกหลัง import โมดูลเสร็จ."""
    for step, label in (
        (_install_log_rotation, "หมุนไฟล์ log"),
        (_apply_schema_filter, "ตัวกรอง odoo.schema"),
    ):
        try:
            step()
        except Exception:  # noqa: BLE001 — ต้องไม่ทำให้โมดูลโหลดล้ม
            _logger.warning(
                "od19_system_monitor: ติดตั้ง %s ไม่สำเร็จ", label, exc_info=True
            )
    _extend_sentry()
