# AGENTS.md — กฎการทำงานของ AI Agent (Odoo 19 CE · AutoInfo)

- **ผลบังคับใช้**: AI agent ทุกตัวที่ทำงานใน repository นี้ (Codex, Claude Code, Trae, Gemini ฯลฯ)
- **สถานะ**: LOCKED — ห้าม agent แก้ไขไฟล์นี้เอง ต้องได้รับอนุมัติจากผู้ใช้เป็นรายครั้ง
- **Revision**: r2 (2026-11-10) — เปลี่ยนจาก *Single-writer* เป็น *Resource-Scoped Lease* เพื่อให้ทำงานขนานได้อย่างปลอดภัย
- Repository: `nattanonvs/odoo19ce-autoinfo` · branch หลัก: `19.0` · ฐานข้อมูลที่ใช้: `odoo19_pdev`

---

## 0. ตัวตนของ agent (AGENT_ID)

ทุก agent ต้องกำหนด `AGENT_ID` ก่อนเริ่มงาน รูปแบบ `<tool>-<worktree>` เช่น
`codex-od19_ai_assistant`, `trae-od19_dashboard`, `claude-od19_iso_risk`

`AGENT_ID` ถูกใช้เป็นชื่อ branch, ชื่อ DB ทดสอบ, ชื่อ data-dir, ชื่อ lease และพอร์ต
เพื่อให้ agent หลายตัวทำงานพร้อมกันได้โดยไม่ชนกัน

**การจัดสรรพอร์ต/DB**

| การใช้งาน | ค่า | หมายเหตุ |
|---|---|---|
| Odoo dev/prod (แชร์) | `8070` | **ห้าม agent รัน/ปิด** ต้องขออนุมัติ |
| Test ต่อ agent | `8081`–`8099` | ผูกกับ AGENT_ID ห้ามซ้ำกัน |
| DB หลัก (แชร์) | `odoo19_pdev`, `odoo19_puat` | ต้องถือ lease ถ้าเขียน |
| DB ทดสอบส่วนตัว | `odoo19_t_<AGENT_ID>` | สร้างจาก template ของตัวเอง |

## 1. ระดับความเสี่ยง และสิทธิ์การอนุมัติ

### Tier 0 — ปลอดภัย ขนานได้ไม่จำกัด (ไม่ต้องขออนุมัติ)

| ประเภท | ตัวอย่าง |
|---|---|
| อ่าน / ค้นหา / ตรวจสอบ | อ่านไฟล์, grep, glob, `git status` / `log` / `diff` / `show` / `fsck` / `branch -a` |
| แก้ไข/สร้างไฟล์ในขอบเขต | ไฟล์ภายใต้ `custom_addons/`, `docs/`, config ของโปรเจกต์ **ใน worktree ของตัวเอง** |
| ตรวจสอบ static | `py_compile`, ตรวจ XML well-formed, linter |
| staging / branch ท้องถิ่น | `git add <path>`, `git restore --staged`, สร้าง branch `feature/*`, `codex/*` |
| เก็บงานชั่วคราว | `git stash push` |
| รัน Unit Test บน **DB ทดสอบส่วนตัว** | `run-tests.ps1 -Database odoo19_t_<AGENT_ID> -HttpPort <ของตัวเอง>` |

### Tier 1 — ขนานได้ตาม namespace (ทำได้เองหลังผ่าน Pre-flight ข้อ 3)

- `git commit` (local) บน branch ของตัวเอง ใน worktree ของตัวเอง
- `git push` เข้า branch งานของตัวเอง (`feature/*`, `codex/*`, `trae/*`)
- แก้ไขโมดูลใน `custom_addons/` ภายใน worktree ของตัวเอง

> commit/push ปลอดภัยพร้อมกันได้ เพราะ worktree มี index แยกกัน และ ref เป็น atomic ต่อ branch

### Tier 2 — ต้องถือ Lease ก่อน (exclusive resource)

- เขียน / `-u` / migration บน DB ที่แชร์ (`odoo19_pdev`, `odoo19_puat`)
- แตะ Odoo instance หรือพอร์ตที่แชร์ (`8070`)
- ลบ/สร้าง filestore หรือ data-dir ของ DB ที่แชร์
- `git worktree add/remove/prune`
- `git gc` / `git repack` / `git fetch --prune`
- แก้ไฟล์ hot นอก worktree: `AGENTS.md`, `odoo.conf`, `run-tests.ps1`, docs กลาง
- ลบ/เปลี่ยนชื่อ branch ที่แชร์

### Tier 3 — HARD LOCK ต้องอนุมัติจากผู้ใช้เป็นรายครั้งเสมอ

| # | การกระทำที่ห้าม | เหตุผล |
|---|---|---|
| 1 | `git push --force` / `--force-with-lease` | เขียนประวัติทับของจริง |
| 2 | push เข้า `19.0` / `main` / `master` โดยตรง | branch หลักต้องผ่านการรีวิว |
| 3 | `git commit --amend` / `rebase` / `squash` / `reset --hard` / history rewrite | เขียนประวัติใหม่ = SHA เปลี่ยนทั้งหมด |
| 4 | `git config` แก้ค่าใด ๆ (รวม `core.hooksPath`) | เปลี่ยนสภาพแวดล้อมของเครื่อง |
| 5 | `git stash drop` / `git clean -fdx` | ลบงานที่ยังไม่ได้ commit |
| 6 | ติดตั้ง / แก้ไข / ลบ ไฟล์ใน `.git/hooks/` | กระทบทุก agent บนเครื่องนี้ |
| 7 | ปิด/รีสตาร์ท Odoo instance ที่แชร์ (`8070`) หรือ Nginx | กระทบผู้ใช้และ agent อื่น |

ข้อยกเว้นข้อ 1–2: ผู้ใช้สั่งอนุมัติเป็นรายครั้ง แล้วตั้งค่า `OD19_PUSH_APPROVED=1` ก่อนสั่ง push

## 2. Resource Lease Protocol (แทน Single-writer)

**หลักการ**: ไม่ล็อกทั้งเครื่องอีกต่อไป — ล็อกเฉพาะ *ทรัพยากร* ที่เขียนร่วมไม่ได้จริง (Tier 2)

**Resource key**: `<type>:<name>` โดย type ∈ `db` `instance` `port` `ref` `file` `git`
ตัวอย่าง: `db:odoo19_pdev`, `port:8070`, `ref:refs/heads/19.0`, `git:gc`, `file:AGENTS.md`

**ไฟล์ lease**: `.agent-locks/<safe-resource>.lock` (JSON) โดยแปลงอักขระที่ไม่ปลอดภัยเป็น `-`
> `.agent-locks/` ต้องอยู่ใน `.gitignore` ห้าม commit

**รูปแบบไฟล์**

```json
{
  "resource": "db:odoo19_pdev",
  "agent_id": "codex-od19_ai_assistant",
  "branch": "feature/od19_ai_assistant",
  "pid": 12345,
  "purpose": "upgrade module od19_ai_assistant",
  "acquired_at": "2026-11-10T12:00:00+07:00",
  "ttl_seconds": 300,
  "heartbeat_at": "2026-11-10T12:03:00+07:00"
}
```

**ขั้นตอน Acquire**

1. สร้างไฟล์แบบ exclusive (`FileMode::CreateNew`) — **ต้อง atomic**
2. ถ้าสร้างไม่ได้ → อ่านไฟล์เดิม แล้วเช็ค:
   - lease หมดอายุ (`now - heartbeat_at > ttl_seconds`) **และ** PID เจ้าของไม่ทำงานอยู่ → เขียนทับได้ (พร้อม log ว่า break lease ของใคร)
   - lease ยังไม่หมดอายุ **หรือ** PID ยังมีชีวิต → **หยุด/รอ** ห้ามเขียนทับ
3. ระหว่างถือ lease ต้อง `Heartbeat` ทุก ≤ 1/3 ของ TTL
4. เลิกงาน (สำเร็จหรือ error) → **ต้อง Release เสมอ** (ใช้ `try/finally`)

**ห้าม** break lease ที่ PID ยังมีชีวิต / ห้ามลบโฟลเดอร์ `.agent-locks` ทั้งก้อน / ห้ามแก้ lease ของ agent อื่น

> **หมายเหตุเรื่อง PID**: `pid` ในไฟล์ lease เป็นเพียง *ข้อมูลประกอบ* สำหรับ debug/audit เท่านั้น — การกันการเขียนทับซ้อนกันจริงยึดที่ **TTL** ไม่ใช่การตรวจ PID เพราะ helper เป็น one-shot child process ที่ตายทันทีหลังคำสั่งจบ จึงให้ตั้ง `-Ttl` ให้ **ครอบเวลางานจริง** (หรือส่ง `-OwnerPid` ของ process ที่อายุยาวกว่า) และ Heartbeat ทุก ≤ 1/3 ของ TTL

**helper ที่ต้องมี**: `agent-lock.ps1 -Action Acquire|Release|Status|Heartbeat -Resource <key> -AgentId <id> -Ttl <sec>`

## 3. Pre-flight (แทนของเดิม 4 ข้อ)

ก่อนเริ่มงานทุกครั้ง:

1. `git log -1 --oneline` → จด HEAD ไว้
2. ระบุ **ชุด resource** ที่งานจะแตะ (Tier 0/1 ไม่ต้องจับ lease)
3. `agent-lock.ps1 -Action Status` → ตรวจว่า resource ที่ต้องการว่าง
4. จับ lease เฉพาะ Tier 2 (`-Action Acquire`)
5. `git status -sb` ใน worktree ของตัวเอง → ต้องสะอาด ไม่มีไฟล์ของ agent อื่นค้าง
6. บันทึก claim (lease) + TTL แล้วเริ่มงาน

ถ้าชน resource → **อย่าหยุดทั้งเครื่อง** ให้เปลี่ยน DB/พอร์ต/ไฟล์ของตัวเองก่อน ถ้าทำไม่ได้จริงจึงรายงานผู้ใช้
(ยกเลิกข้อ "HEAD ต้องไม่เปลี่ยนภายใน 2 นาที" — ไม่จำเป็นอีกเมื่อแยก worktree/lease)

## 4. กฎการ commit (Tier 1 — ทำได้เองหลังผ่าน Pre-flight)

- **ต้องรัน Unit Test ให้ผ่านก่อน commit/push** (0 failed / 0 error) — บน DB ทดสอบของตัวเอง
- รูปแบบ Conventional Commits: `<type>(<scope>): <description>`
  - type: `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`
- 1 commit = 1 โดเมนงาน ห้ามรวมหลายโดเมนใน commit เดียว
- บรรทัดแรกใช้ present tense / imperative mood และยาวไม่เกิน 72 ตัวอักษร
- ระบุไฟล์เป็นรายชื่อชัดเจน (`git add <path>` หรือ `git commit -- <path>`) **ห้าม** `git add -A` หรือ `git add .`
- ห้าม commit ไฟล์ที่ `.gitignore` ครอบไว้ — ตรวจก่อนด้วย `git check-ignore -v --no-index <path>`

## 5. กฎการ push (Tier 1 — branch งานตัวเอง)

- push ได้เฉพาะ branch งานของตัวเอง (`feature/*`, `codex/*`, `trae/*`)
- ห้าม push ตรงเข้า `19.0` / `main` / `master`
- **ห้าม rebase / force branch ที่ push ขึ้น remote แล้ว** (ยกเว้น branch ตัวเองที่ยังไม่มีใครใช้)
- ถ้า push ถูก reject เพราะ remote ใหม่กว่า → หยุดและรายงาน ห้ามใช้ force
- หลัง push ต้องรายงาน URL ของ commit/PR ให้ผู้ใช้ทราบ

## 6. การทดสอบแบบขนาน

- ใช้ **DB ทดสอบส่วนตัว** `odoo19_t_<AGENT_ID>` + `-DataDir` + `-HttpPort` ของตัวเอง
  (`run-tests.ps1` มีพารามิเตอร์ `-Database` `-DataDir` `-HttpPort` อยู่แล้ว)
- **ห้ามรัน `-u` (upgrade) บน DB ที่แชร์** จากงานประจำ — ถ้าจำเป็นต้องได้ lease `db:<ชื่อ>` ก่อน
- ห้ามรัน Odoo สองตัวบน DB เดียวกันโดยใช้ filestore ต่างกัน (ทำให้ asset bundle พัง 404 / จอขาว)
- เตรียม DB จาก template: `CREATE DATABASE odoo19_t_<AGENT_ID> WITH TEMPLATE <template> OWNER <owner>` + copy `data_dir/filestore/<db>`

## 7. กฎทั่วไปของโปรเจกต์

- ห้ามแก้ไฟล์ core ของ Odoo (`odoo/`, `addons/`) — แก้ได้เฉพาะ `custom_addons/` และ config ของโปรเจกต์
- ห้ามฝัง credential ลงในคำสั่ง/สคริปต์ ให้อ่านค่าจาก `odoo.conf` ตอนรัน
- ใช้ฐานข้อมูลหลัก `odoo19_pdev` สำหรับงานที่แชร์ (งานส่วนตัวใช้ DB ทดสอบของตัวเอง)
- สคริปต์ `.ps1` ต้องเป็น UTF-8 **with BOM** เพื่อกัน parsing error ภาษาไทยบน Windows
- ใช้ PowerShell 7 (pwsh) รันสคริปต์เพื่อรองรับ UTF-8

## 8. ความปลอดภัยของข้อมูลลับ (Security)

ห้าม commit ไฟล์เหล่านี้เด็ดขาด:

- `odoo.conf` (มี `db_password`) — ถูก ignore ที่ `.gitignore:28` แล้ว
- `.env`, `*.key`, `*.pem`, `*.p12`, `id_rsa*`, `credentials*.json`
- `backups/` (ข้อมูลจริง) — ignore ที่ `.gitignore:69`
- `data/`, `data_test/`, `venv19/`, `pylibs/`, `wkhtmltopdf/bin/`, `.agent-locks/`

ก่อน commit ทุกครั้ง ให้ตรวจ `git diff --cached --name-only` ว่าไม่มีไฟล์ตามรายการข้างต้น

## 9. การสร้าง worktree/branch เมื่อมีการเพิ่มโมดูล

- เมื่อ agent จะ **สร้างโมดูลใหม่** หรือ **แก้ไขโมดูลหลายตัว** ให้สร้าง **worktree แยก + branch เฉพาะงาน** ทุกครั้ง — ห้ามปนงานลง branch หลักโดยตรง
- **ชื่อ branch/worktree ให้อ้างอิงจากชื่อ "โมดูลแรก"** ที่เริ่มสร้างหรือแก้ไขในงานรอบนั้น
  - 1 โมดูล → `feature/<โมดูลแรก>` เช่น `feature/od19_hr_expense_enhanced`
  - หลายโมดูล → ใช้ **ชื่อโมดูลแรก** เป็นชื่อหลัก แล้วต่อท้ายด้วยขอบเขตงานสั้น ๆ เช่น `feature/<โมดูลแรก>-<scope>`
  - worktree directory ตั้งชื่อให้สื่อกับ branch เช่น `c:\odoo-dev\<โมดูลแรก-ย่อ>`
- ลำดับ "โมดูลแรก" = โมดูลที่ถูกสร้าง/แก้ไขเป็นอันดับแรกสุดในงานรอบนั้น ถ้าไม่ชัดเจนให้ยึดโมดูลหลักที่ผูกกับโดเมนของงาน
- `git worktree add/remove/prune` เป็น Tier 2 → ต้องถือ lease `git:worktree`

## 10. ก่อนรายงานผลทุกครั้ง

ระบุให้ครบ: AGENT_ID, commit SHA (ถ้ามี), ไฟล์ที่แตะ, lease ที่จับ/ปล่อย, คำสั่งที่รันจริง, ผลลัพธ์จริง — ห้ามอ้างผลที่ยังไม่ได้รัน
