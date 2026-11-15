# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ค่าคงที่ที่ใช้ร่วมกันทั้งโมดูล (ระดับความรุนแรง สถานะ ตัวดำเนินการ).

แยกออกมาเป็นโมดูลเดี่ยวเพื่อให้ทุกโมเดล (rule / check / result / incident)
อ้างอิง "พจนานุกรม" ชุดเดียวกัน ป้องกันการพิมพ์ค่าซ้ำแล้วไม่ตรงกัน
"""

# ระดับความรุนแรง 4 ระดับตามข้อเสนอโครงการ P3
SEVERITIES = [
    ("info", "Info"),
    ("warning", "Warning"),
    ("critical", "Critical"),
    ("emergency", "Emergency"),
]

# ลำดับตัวเลขของความรุนแรง — ใช้เทียบ "ยกระดับ" และเลือกกฎที่รุนแรงสุด
SEVERITY_RANK = {
    "info": 10,
    "warning": 20,
    "critical": 30,
    "emergency": 40,
}

# สถานะผลการตรวจ (สรุปให้เหลือ 3 ระดับสำหรับ dashboard)
CHECK_STATES = [
    ("unknown", "ไม่ทราบ"),
    ("ok", "ปกติ"),
    ("warning", "เตือน"),
    ("critical", "วิกฤต"),
]

STATE_RANK = {"unknown": 0, "ok": 0, "warning": 1, "critical": 2}

# ความรุนแรง -> สถานะที่แสดงบน dashboard
SEVERITY_TO_STATE = {
    "info": "ok",
    "warning": "warning",
    "critical": "critical",
    "emergency": "critical",
}

# สีสถานะตามสไตล์ od19_dashboard (red/yellow/green/grey)
STATE_TO_COLOR = {
    "unknown": "grey",
    "ok": "green",
    "warning": "yellow",
    "critical": "red",
}

# ตัวดำเนินการเปรียบเทียบสำหรับ rule engine
OPERATORS = [
    ("gt", ">"),
    ("ge", ">="),
    ("lt", "<"),
    ("le", "<="),
    ("eq", "="),
    ("ne", "!="),
    ("contains", "มีคำว่า"),
]

# แหล่งค่าที่กฎจะนำมาเทียบ
METRICS = [
    ("value", "ค่าที่วัด (ตัวเลข)"),
    ("status", "สถานะ (ข้อความ)"),
    ("message", "ข้อความผลตรวจ"),
    ("always", "ตรงเสมอ (เมื่อตรวจล้มเหลว)"),
]

# ir.config_parameter keys
PARAM_ENABLED = "od19_health.enabled"
PARAM_RETENTION_DAYS = "od19_health.retention_days"
PARAM_DIGEST_ENABLED = "od19_health.digest_enabled"
PARAM_DIGEST_HOUR = "od19_health.digest_hour"
PARAM_AI_TRIAGE_ENABLED = "od19_health.ai_triage_enabled"
PARAM_LOG_ROTATION_ENABLED = "od19_health.log_rotation_enabled"
PARAM_LOG_MAX_BYTES = "od19_health.log_max_bytes"
PARAM_LOG_BACKUP_COUNT = "od19_health.log_backup_count"
PARAM_DATA_DIR = "od19_health.data_dir"
PARAM_HEARTBEAT_TOKEN = "od19_health.heartbeat_token"

DEFAULT_RETENTION_DAYS = 90
DEFAULT_DIGEST_HOUR = 8
DEFAULT_MAX_AGE_MINUTES = 30
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 10

# event key ที่ส่งให้ od19_notification_multi_channel
NOTIFY_EVENT_ALERT = "od19_health_alert"
NOTIFY_EVENT_DIGEST = "od19_health_digest"


def human_bytes(size):
    """แปลงจำนวนไบต์เป็นข้อความอ่านง่าย (KB/MB/GB/TB)."""
    try:
        value = float(size or 0)
    except (TypeError, ValueError):
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0:
            return "%.1f %s" % (value, unit)
        value /= 1024.0
    return "%.1f PB" % value


def compare(operator, left, right):
    """เทียบ ``left`` กับ ``right`` ตาม ``operator`` (คืน False เมื่อเทียบไม่ได้)."""
    if operator == "contains":
        return str(right or "") in str(left or "")
    try:
        left_num = float(left)
        right_num = float(right)
    except (TypeError, ValueError):
        # เทียบแบบข้อความเมื่อไม่ใช่ตัวเลข (เช่น status eq down)
        if operator == "eq":
            return str(left) == str(right)
        if operator == "ne":
            return str(left) != str(right)
        return False
    if operator == "gt":
        return left_num > right_num
    if operator == "ge":
        return left_num >= right_num
    if operator == "lt":
        return left_num < right_num
    if operator == "le":
        return left_num <= right_num
    if operator == "eq":
        return left_num == right_num
    if operator == "ne":
        return left_num != right_num
    return False
