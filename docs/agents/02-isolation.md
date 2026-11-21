# 02. Isolation (การแยกตัวตน · worktree · port/DB · Pre-flight)

> **EN**: Every agent runs as an isolated tenant with its own `AGENT_ID`, worktree, test DB and port. · **TH**: ทุก agent ทำงานแบบแยกส่วน มี AGENT_ID, worktree, DB ทดสอบ และพอร์ตของตัวเอง

## 1. AGENT_ID

ทุก agent **ต้องกำหนด `AGENT_ID` ก่อนเริ่มงาน** รูปแบบ `<tool>-<worktree>` เช่น
`codex-od19_ai_assistant`, `trae-od19_dashboard`, `claude-od19_iso_risk`

`AGENT_ID` ถูกใช้เป็นชื่อ branch, ชื่อ DB ทดสอบ, ชื่อ data-dir, ชื่อ lease และพอร์ต เพื่อให้ agent หลายตัวทำงานพร้อมกันได้โดยไม่ชนกัน

## 2. การจัดสรรพอร์ต/DB

| การใช้งาน | ค่า | หมายเหตุ |
|---|---|---|
| Odoo dev/prod (แชร์) | `8070` | **ห้าม agent รัน/ปิด** ต้องขออนุมัติ — **ยกเว้น** deploy+restart ใน S1 (ดู [04-delivery.md §2](04-delivery.md)) |
| Test ต่อ agent | `8081`–`8099` | ผูกกับ AGENT_ID ห้ามซ้ำกัน |
| DB หลัก (แชร์) | `odoo19_pdev`, `odoo19_puat` | ต้องถือ lease ถ้าเขียน |
| DB ทดสอบส่วนตัว | `odoo19_t_<AGENT_ID>` | สร้างจาก template ของตัวเอง |

## 3. Worktree & Branch Naming (การสร้าง worktree/branch)

- เมื่อ agent จะ **สร้างโมดูลใหม่** หรือ **แก้ไขโมดูลหลายตัว** ให้สร้าง **worktree แยก + branch เฉพาะงาน** ทุกครั้ง — ห้ามปนงานลง branch หลักโดยตรง
- **ชื่อ branch/worktree ให้อ้างอิงจากชื่อ "โมดูลแรก"** ที่เริ่มสร้างหรือแก้ไขในงานรอบนั้น
  - 1 โมดูล → `feature/<โมดูลแรก>` เช่น `feature/od19_hr_expense_enhanced`
  - หลายโมดูล → ใช้ **ชื่อโมดูลแรก** เป็นชื่อหลัก แล้วต่อท้ายด้วยขอบเขตงานสั้น ๆ เช่น `feature/<โมดูลแรก>-<scope>`
  - worktree directory ตั้งชื่อให้สื่อกับ branch เช่น `c:\odoo-dev\<โมดูลแรก-ย่อ>`
- ลำดับ "โมดูลแรก" = โมดูลที่ถูกสร้าง/แก้ไขเป็นอันดับแรกสุดในงานรอบนั้น ถ้าไม่ชัดเจนให้ยึดโมดูลหลักที่ผูกกับโดเมนของงาน
- `git worktree add/remove/prune` เป็น **Shared-Resource** → ต้องถือ lease `git:worktree`

## 4. Worktree Hygiene (วินัย worktree — ป้องกันข้อมูลหายและงานปะปน)

หลักการ: ทุก worktree ต้อง "มีบ้าน" (branch) เสมอ · ไฟล์ของ agent อื่นห้ามแตะ · การ deploy ต้องตรวจสอบย้อนกลับได้

- **ห้ามปล่อย worktree ไว้ที่ detached HEAD** — commit บน detached HEAD ไม่มี ref หนุน เสี่ยงถูก `git gc` เก็บทิ้ง
  - ก่อนเริ่มงานใน worktree ใด ๆ ให้ตรวจ `git -C <wt> status --porcelain --branch` ว่าไม่ใช่ `HEAD (no branch)`
  - ถ้า detached → สร้าง branch คลุมทันที: `git -C <wt> switch -c feature/<โมดูลแรก>-<scope>` (Write-Scope)
  - ตรวจเป็นรอบด้วย `git worktree list` — ต้องไม่มีแถวที่ขาด `[branch]`
- **ไฟล์ทดลอง/โพรบต้องไม่ค้างใน worktree** — ไฟล์ `_*.py`, `_*.txt`, `*.bak`, `data_test_*` ถ้าใช้ชั่วคราว ให้เก็บในโฟลเดอร์ที่ `.gitignore` ครอบ หรือย้ายออกนอก repo
  - ถ้าพบ untracked ที่ **ไม่ใช่ของตัวเอง** → **ห้ามลบ** ให้รายงานเจ้าของงาน
- **แยกขอบเขต deploy (release worktree)** — instance หลักโหลด addons จาก `C:\odoo-dev\od19_release\custom_addons`
  - ห้าม `git add -A` / `git add .` ใน release worktree (มักมีไฟล์ agent อื่นค้าง) — ใช้ `git add -- <path>` เจาะจงเสมอ
  - ก่อน commit ให้ `git diff --cached --name-only` ยืนยันว่าไม่มีไฟล์ของ agent อื่น/ไฟล์ต้องห้ามติดไป
- **ยืนยันโค้ดที่ deploy ก่อน restart/สลับเวอร์ชัน** — ตรวจว่าไฟล์ที่ deploy ตรงกับ tip ของ branch งาน:
  `git diff --stat <dev-sha>:<path> <deploy-sha>:<path>` ต้องว่าง (เหมือนกันทุกไบต์)
- **dump สำรองก่อน `-u`/migration ที่กระทบข้อมูล** — ยกเว้นได้รับอนุมัติเป็นรายครั้ง
- **หลีกเลี่ยง `STEP-3-Start-Odoo19.ps1`** — blast radius กว้าง (kill Odoo/nginx ทั้งหมด + ตัด PG session ของ DB อื่น + หมุน log) ให้ใช้เฉพาะเมื่อจำเป็นจริง; restart ปกติให้เจาะจง PID (`Stop-Process -Id <pid>`) แล้วเริ่ม command line เดิม
- **ตรวจ submodule ก่อนแตะ `third_party/oca/*`** — `git submodule status` ต้องขึ้นต้นด้วยช่องว่าง (space = sync) ทั้งหมด; ถ้าเจอ `+` หรือ `-` ให้แก้ให้ตรงก่อน

## 5. Pre-flight (ตรวจก่อนเริ่มงาน)

ก่อนเริ่มงานทุกครั้ง:

1. `git log -1 --oneline` → จด HEAD ไว้
2. ระบุ **ชุด resource** ที่งานจะแตะ (Read/Write-Scope ไม่ต้องจับ lease)
3. `agent-lock.ps1 -Action Status` → ตรวจว่า resource ที่ต้องการว่าง
4. จับ lease เฉพาะ **Shared-Resource** (`-Action Acquire`) — ดู [03-lease.md](03-lease.md)
5. `git status -sb` ใน worktree ของตัวเอง → ต้องสะอาด ไม่มีไฟล์ของ agent อื่นค้าง
6. อ่าน ledger ของ Delivery Pipeline (`.agent-locks/delivery-pipeline.json`) เพื่อดูว่ามีงานใดถึงกรอบเวลาที่ต้องเลื่อน stage หรือ cleanup — ดู [04-delivery.md](04-delivery.md)

## 6. Parallel Testing (การทดสอบแบบขนาน)

- ใช้ **DB ทดสอบส่วนตัว** `odoo19_t_<AGENT_ID>` + `-DataDir` + `-HttpPort` ของตัวเอง (`run-tests.ps1` มีพารามิเตอร์ `-Database` `-DataDir` `-HttpPort` อยู่แล้ว)
- การติดตั้ง (`-i`) / อัปเดต (`-u`) โมดูล ต้องถือ lease `db:<ชื่อ>` ก่อนเสมอ
- ห้ามรัน Odoo สองตัวบน DB เดียวกันโดยใช้ filestore ต่างกัน (ทำให้ asset bundle พัง 404 / จอขาว)
- เตรียม DB จาก template: `CREATE DATABASE odoo19_t_<AGENT_ID> WITH TEMPLATE <template> OWNER <owner>` + copy `data_dir/filestore/<db>`
