# 01. Capabilities & Approval (ระดับความสามารถและสิทธิ์อนุมัติ)

> **EN**: Four capabilities replace the old Tier 0–3. Each rule lists what you may do and which gate (if any) you must pass. · **TH**: ใช้ 4 capability แทน Tier 0–3 เดิม แต่ละข้อระบุสิ่งที่ทำได้และด่านที่ต้องผ่านก่อนลงมือ

## 1. Read (อ่าน)

**Gate**: ไม่ต้องอนุมัติ · ขนานได้ไม่จำกัด (no approval · unlimited parallel)

**ทำได้**
- อ่านไฟล์, ค้นหา (`grep`, `glob`)
- `git status` / `log` / `diff` / `show` / `fsck` / `branch -a`
- ตรวจสอบ static: `py_compile`, ตรวจ XML well-formed, linter

## 2. Write-Scope (แก้ในขอบเขตของตัวเอง)

**Gate**: ทำได้เองหลังผ่าน **Pre-flight** — ดู [02-isolation.md §5](02-isolation.md#5-pre-flight-ตรวจก่อนเริ่มงาน)

**ทำได้**
- แก้/สร้างไฟล์ภายใต้ `custom_addons/`, `docs/`, config ของโปรเจกต์ **ใน worktree ของตัวเอง**
- staging: `git add <path>`, `git restore --staged`
- สร้าง branch ของตัวเอง: `feature/*`, `codex/*`, `trae/*`
- เก็บงานชั่วคราว: `git stash push`
- `git commit` (local) บน branch ของตัวเอง ใน worktree ของตัวเอง
- `git push` เข้า branch งานของตัวเอง (`feature/*`, `codex/*`, `trae/*`)
- รัน Unit Test บน **DB ทดสอบส่วนตัว**: `run-tests.ps1 -Database odoo19_t_<AGENT_ID> -HttpPort <ของตัวเอง>`

> commit/push ปลอดภัยพร้อมกันได้ เพราะ worktree มี index แยกกัน และ ref เป็น atomic ต่อ branch

## 3. Shared-Resource (ทรัพยากรแชร์ → ต้องถือ lease)

**Gate**: **ต้องถือ lease** ก่อนทุกครั้ง — ดู [03-lease.md](03-lease.md)

- เขียน / `-u` / migration บน DB ที่แชร์ (`odoo19_pdev`, `odoo19_puat`)
- แตะ Odoo instance หรือพอร์ตที่แชร์ (`8070`)
- ลบ/สร้าง filestore หรือ data-dir ของ DB ที่แชร์
- `git worktree add/remove/prune`
- `git gc` / `git repack` / `git fetch --prune`
- แก้ไฟล์ hot นอก worktree: `AGENTS.md`, `docs/agents/*`, `odoo.conf`, `run-tests.ps1`, docs กลาง
- ลบ/เปลี่ยนชื่อ branch ที่แชร์
- **Auto-cleanup ของ Delivery Pipeline** (S4) — ดู [04-delivery.md §6](04-delivery.md#6-s4--verify-7-วัน--auto-cleanup)

## 4. Destructive (HARD LOCK)

**Gate**: **อนุมัติจากผู้ใช้เป็นรายครั้งเสมอ** (per-instance approval) — ห้ามทำเองโดยเด็ดขาด

| # | การกระทำที่ห้าม | เหตุผล |
|---|---|---|
| 1 | `git push --force` / `--force-with-lease` | เขียนประวัติทับของจริง |
| 2 | push เข้า `19.0` / `main` / `master` โดยตรง | branch หลักต้องผ่านการรีวิว |
| 3 | `git commit --amend` / `rebase` / `squash` / `reset --hard` / history rewrite | เขียนประวัติใหม่ = SHA เปลี่ยนทั้งหมด |
| 4 | `git config` แก้ค่าใด ๆ (รวม `core.hooksPath`) | เปลี่ยนสภาพแวดล้อมของเครื่อง |
| 5 | `git stash drop` / `git clean -fdx` | ลบงานที่ยังไม่ได้ commit |
| 6 | ติดตั้ง / แก้ไข / ลบ ไฟล์ใน `.git/hooks/` | กระทบทุก agent บนเครื่องนี้ |
| 7 | ปิด/รีสตาร์ท Odoo instance ที่แชร์ (`8070`) หรือ Nginx | กระทบผู้ใช้และ agent อื่น |

**ข้อยกเว้นข้อ 1–2**: ผู้ใช้สั่งอนุมัติเป็นรายครั้ง แล้วตั้งค่า `OD19_PUSH_APPROVED=1` ก่อนสั่ง push

## 5. กฎตัดสินเมื่อไม่แน่ใจ (Decision rule)

- ถ้าคำสั่งหนึ่งเข้าข่ายได้หลาย capability → ยึด **ระดับสูงสุด** ที่เข้าข่าย
- ถ้าชน resource → **อย่าหยุดทั้งเครื่อง** ให้เปลี่ยน DB/พอร์ต/ไฟล์ของตัวเองก่อน ถ้าทำไม่ได้จริงจึงรายงานผู้ใช้
