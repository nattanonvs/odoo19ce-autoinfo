# 03. Resource Lease Protocol (พิธีการจอง lease)

> **EN**: Lock only the resources that genuinely cannot be written concurrently (Shared-Resource). · **TH**: ไม่ล็อกทั้งเครื่อง — ล็อกเฉพาะ *ทรัพยากร* ที่เขียนร่วมไม่ได้จริง (Shared-Resource)

## 1. Resource key

รูปแบบ `<type>:<name>` โดย type ∈ `db` `instance` `port` `ref` `file` `git`
ตัวอย่าง: `db:odoo19_pdev`, `port:8070`, `ref:refs/heads/19.0`, `git:gc`, `file:AGENTS.md`

## 2. ไฟล์ lease

`.agent-locks/<safe-resource>.lock` (JSON) โดยแปลงอักขระที่ไม่ปลอดภัยเป็น `-`
> `.agent-locks/` ต้องอยู่ใน `.gitignore` ห้าม commit

### รูปแบบไฟล์

```json
{
  "resource": "db:odoo19_pdev",
  "agent_id": "codex-od19_ai_assistant",
  "branch": "feature/od19_ai_assistant",
  "pid": 12345,
  "purpose": "upgrade module od19_ai_assistant",
  "acquired_at": "2026-11-20T12:00:00+07:00",
  "ttl_seconds": 300,
  "heartbeat_at": "2026-11-20T12:03:00+07:00"
}
```

## 3. ขั้นตอน Acquire

1. สร้างไฟล์แบบ exclusive (`FileMode::CreateNew`) — **ต้อง atomic**
2. ถ้าสร้างไม่ได้ → อ่านไฟล์เดิม แล้วเช็ค:
   - lease หมดอายุ (`now - heartbeat_at > ttl_seconds`) **และ** PID เจ้าของไม่ทำงานอยู่ → เขียนทับได้ (พร้อม log ว่า break lease ของใคร)
   - lease ยังไม่หมดอายุ **หรือ** PID ยังมีชีวิต → **หยุด/รอ** ห้ามเขียนทับ
3. ระหว่างถือ lease ต้อง `Heartbeat` ทุก ≤ 1/3 ของ TTL
4. เลิกงาน (สำเร็จหรือ error) → **ต้อง Release เสมอ** (ใช้ `try/finally`)

**ห้าม** break lease ที่ PID ยังมีชีวิต / ห้ามลบโฟลเดอร์ `.agent-locks` ทั้งก้อน / ห้ามแก้ lease ของ agent อื่น

> **หมายเหตุเรื่อง PID**: `pid` ในไฟล์ lease เป็นเพียง *ข้อมูลประกอบ* สำหรับ debug/audit เท่านั้น — การกันการเขียนทับซ้อนกันจริงยึดที่ **TTL** ไม่ใช่การตรวจ PID เพราะ helper เป็น one-shot child process ที่ตายทันทีหลังคำสั่งจบ จึงให้ตั้ง `-Ttl` ให้ **ครอบเวลางานจริง** (หรือส่ง `-OwnerPid` ของ process ที่อายุยาวกว่า) และ Heartbeat ทุก ≤ 1/3 ของ TTL

## 4. helper ที่ต้องมี

```
agent-lock.ps1 -Action Acquire|Release|Status|Heartbeat -Resource <key> -AgentId <id> -Ttl <sec>
```
