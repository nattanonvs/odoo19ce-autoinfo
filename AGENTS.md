# AGENTS.md — กฎการทำงานของ AI Agent (Odoo 19 CE · AutoInfo)

> **EN**: Index only. Detailed rules live in `docs/agents/*.md`. · **TH**: ไฟล์นี้เป็น **ดัชนีเท่านั้น** กฎฉบับละเอียดอยู่ใน `docs/agents/*.md`

- **ผลบังคับใช้ (Scope)**: AI agent ทุกตัวที่ทำงานใน repository นี้ (Codex, Claude Code, Trae, Gemini ฯลฯ)
- **สถานะ (Status)**: **LOCKED** — agent **ห้ามแก้** ไฟล์นี้และไฟล์ใน `docs/agents/` เอง ต้องได้อนุมัติจากผู้ใช้เป็นรายครั้ง
- **Revision**: r6 (2026-11-20) — ยกเครื่องโครงสร้าง: แยกไฟล์โมดูลาร์ + **Capability-based** model (แทน Tier 0–3) + **Delivery Pipeline แบบ time-box** (24 ชม./24 ชม./7 วัน)
- **Revision history**: r5 (2026-11-19) pdev-first delivery · r4 (2026-11-19) worktree hygiene · r3 (2026-11-12) self install/update + counter · r2 (2026-11-10) Resource-Scoped Lease (แทน Single-writer)
- **Repository**: `nattanonvs/odoo19ce-autoinfo` · branch หลัก `19.0` · ฐานข้อมูลหลัก `odoo19_pdev`

---

## สารบัญ (Index)

| ไฟล์ | เนื้อหา | เดิมคือ |
|---|---|---|
| [01-capabilities.md](docs/agents/01-capabilities.md) | 4 capability + ตารางคำสั่ง + การขออนุมัติ | §1 |
| [02-isolation.md](docs/agents/02-isolation.md) | AGENT_ID · worktree · port/DB · Pre-flight · ทดสอบขนาน | §0 §3 §6 §9 §12 |
| [03-lease.md](docs/agents/03-lease.md) | Resource Lease Protocol | §2 |
| [04-delivery.md](docs/agents/04-delivery.md) | Delivery Pipeline (time-box) · commit · push · deploy | §4 §5 §11 |
| [05-security.md](docs/agents/05-security.md) | Secrets · ห้ามแก้ core · ไฟล์ต้องห้าม commit | §7 §8 |
| [06-quality.md](docs/agents/06-quality.md) | Test gate · verify-before-claim · การรายงานผล | §10 |

---

## Capability (4 ระดับ)

| Capability | ตัวอย่าง | Gate |
|---|---|---|
| **Read** | อ่าน/grep/glob, `git status·log·diff·show·fsck·branch -a` | ไม่ต้องอนุมัติ · ขนานไม่จำกัด |
| **Write-Scope** | แก้ `custom_addons/`·`docs/`·config ใน worktree ตัวเอง; commit/push branch ตัวเอง | ทำได้เองหลังผ่าน Pre-flight |
| **Shared-Resource** | เขียน/`-u` บน DB แชร์, port `8070`, `git worktree/gc`, ไฟล์ hot (`AGENTS.md`, `odoo.conf`, `run-tests.ps1`) | **ต้องถือ lease** |
| **Destructive** | `push --force` · push เข้า `19.0/main` · amend/rebase/`reset --hard` · `git config` · `stash drop`/`clean -fdx` · `.git/hooks/` · ปิด/รีสตาร์ท `8070`/nginx | **HARD LOCK** อนุมัติรายครั้ง |

---

## พอร์ต / DB

| การใช้งาน | ค่า | หมายเหตุ |
|---|---|---|
| Odoo dev/prod (แชร์) | `8070` | **ห้าม agent รัน/ปิด** ต้องขออนุมัติ |
| Test ต่อ agent | `8081`–`8099` | ผูกกับ AGENT_ID ห้ามซ้ำ |
| DB หลัก (แชร์) | `odoo19_pdev`, `odoo19_puat` | ต้องถือ lease ถ้าเขียน |
| DB ทดสอบส่วนตัว | `odoo19_t_<AGENT_ID>` | สร้างจาก template ของตัวเอง |
| Release addons path | `C:\odoo-dev\od19_release\custom_addons` | instance หลักโหลดจากที่นี่ |

---

## Delivery Pipeline อย่างย่อ (time-box)

1. **S1**: แก้/สร้างโมดูล + **Test ผ่าน** → ติดตั้ง/อัปเดต `odoo19_pdev` + commit (แยกโดเมน) ทันที
2. **S2**: **+24 ชม.** ไม่มีคำสั่ง/ผลตรวจ → ถือว่าผ่าน → ติดตั้ง `odoo19_puat` + **push**
3. **S3**: **+24 ชม.** ไม่มีคำสั่ง → ถือว่าผ่าน → **เปิด PR** (feature/* → `19.0`) แล้ว **รออนุมัติ merge**
4. **S4**: merge เข้า `19.0` แล้ว **+7 วัน** → ตรวจไฟล์ตรงกันทุกไบต์ → **auto-cleanup** ลบ source branch/worktree + ไฟล์ TEST + DB TEST

> รายละเอียด pipeline, ledger และ override อยู่ที่ [04-delivery.md](docs/agents/04-delivery.md)
