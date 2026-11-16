ISSUE_STREAM_SELECTION = [
    ("it_support", "ไอที/ระบบ (IT Support)"),
    ("improvement", "ข้อเสนอแนะปรับปรุง"),
    ("iso_capa", "คุณภาพ / ISO (CAPA)"),
    ("unsure", "ไม่แน่ใจ"),
]

IMPACT_SELECTION = [
    ("I1", "เฉพาะตัวเอง"),
    ("I2", "หลายแผนก / หลายคน"),
    ("I3", "กระทบทั้งบริษัท / ระบบหยุดทั้งระบบ"),
]

URGENCY_SELECTION = [
    ("U1", "ไม่กระทบ (ทำงานได้ตามปกติ)"),
    ("U2", "มีผล แต่มีงานแทนชั่วคราว"),
    ("U3", "หยุดงานทันที"),
]

VISIBILITY_SELECTION = [
    ("public", "สาธารณะ (ทุกคน)"),
    ("department", "เฉพาะแผนก"),
    ("private", "ส่วนตัว"),
]

CONSENT_SELECTION = [
    ("pending", "รอยินยอม"),
    ("accepted", "ยินยอม (เข้าคิว)"),
    ("jump_requested", "ขอแซงคิว"),
]

QUEUE_REQUEST_STATE = [
    ("draft", "ร่าง"),
    ("waiting_reporter_head", "รอหัวหน้าแผนกผู้แจ้ง"),
    ("waiting_team_head", "รอหัวหน้าทีมเจ้าของคิว"),
    ("approved", "อนุมัติแล้ว"),
    ("rejected", "ปฏิเสธ"),
    ("expired", "หมดอายุ"),
]

# score = Impact + Urgency (2..6) -> OCA priority ("0".."3")
# 6 -> P3 ด่วนวิกฤต, 5 -> P2 สูง, 3-4 -> P1 กลาง, 2 -> P0 ต่ำ
_SCORE_TO_PRIORITY = {6: "3", 5: "2", 4: "1", 3: "1", 2: "0"}

# ป้ายอธิบาย priority ที่คำนวณได้ (ใช้แสดงใน chatter/audit)
PRIORITY_LABEL = {
    "3": "ด่วนวิกฤต (P3)",
    "2": "สูง (P2)",
    "1": "กลาง (P1)",
    "0": "ต่ำ (P0)",
}


def score_to_priority(impact, urgency):
    """แปลง Impact + Urgency (ผลรวม 2..6) เป็นค่า priority ของ OCA ('0'..'3')."""
    i = int(impact[1]) if impact else 1
    u = int(urgency[1]) if urgency else 1
    return _SCORE_TO_PRIORITY.get(i + u, "1")
