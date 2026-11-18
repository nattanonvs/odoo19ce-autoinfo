"""STEP-5 : ตรวจสอบความสมบูรณ์ของไฟล์สำรอง Odoo 19 ด้วยการกู้คืนจริง (restore drill).

วัตถุประสงค์:
    ยืนยันว่าไฟล์สำรองล่าสุด "กู้คืนได้จริง" ไม่ใช่แค่มีไฟล์อยู่บนดิสก์
    ออกแบบให้ทำงานเป็นงานรายสัปดาห์ผ่าน Windows Task Scheduler
    (ตัวห่อ: STEP-5-Verify-Backup-Odoo19.ps1)

ขั้นตอน:
    1. เลือกไฟล์สำรองล่าสุด (*.dump.zip / *.dump) ในโฟลเดอร์สำรอง
    2. ตรวจ size + sha256 เทียบกับบันทึกใน backups/backup-manifest.jsonl (ถ้ามี)
    3. กู้คืนลงฐานข้อมูลชั่วคราว (ค่าเริ่มต้น odoo19_restoretest)
       ด้วย odoo.service.db.restore_db(copy=True)
    4. ตรวจตารางหลัก + จำนวนแถวสำคัญ
    5. ลบฐานข้อมูลชั่วคราวทิ้งเสมอ (try/finally)

คืนค่า exit: 0 = ผ่าน, 1 = ไม่ผ่าน

ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น
    (ฐานข้อมูลชั่วคราวใช้เฉพาะระหว่างตรวจสอบ และถูกลบทุกครั้ง)

ใช้งาน:
    venv19\\Scripts\\python.exe STEP-5-Verify-Backup-Odoo19.py [--conf odoo.conf] [--db odoo19_pdev]
"""

import argparse
import glob
import hashlib
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ตารางหลักที่ต้องตรวจหลังกู้คืน: {ชื่อตาราง: จำนวนแถวขั้นต่ำที่ต้องมี}
REQUIRED_TABLES = {
    "res_users": 1,
    "res_company": 1,
    "ir_module_module": 1,
    "ir_config_parameter": 1,
    "orm_signaling_registry": 0,  # ตาราง signaling ของ Odoo 19 (แค่ต้องมีตาราง)
}


def _sha256_and_size(path):
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def _newest_backup(folder):
    files = []
    for pattern in ("*.dump.zip", "*.dump"):
        files.extend(glob.glob(os.path.join(folder, pattern)))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _manifest_entries(manifest_path):
    entries = []
    if not os.path.exists(manifest_path):
        return entries
    with open(manifest_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def main():
    parser = argparse.ArgumentParser(description="Odoo 19 backup restore drill (STEP-5)")
    parser.add_argument("--conf", default=os.path.join(PROJECT_ROOT, "odoo.conf"))
    parser.add_argument("--db", default="odoo19_pdev", help="source database (default: odoo19_pdev)")
    parser.add_argument("--folder", default=os.path.join(PROJECT_ROOT, "backups"), help="backup folder")
    parser.add_argument("--temp-db", default="odoo19_restoretest", help="temporary restore database name")
    args = parser.parse_args()

    from odoo.tools import config as odoo_config

    odoo_config.parse_config(["-c", args.conf, "--database", args.db])

    # ปลดล็อกเฉพาะโปรเซสนี้ - จำเป็นสำหรับ restore_db / exp_drop (@check_db_management_enabled)
    odoo_config["list_db"] = True

    import odoo.sql_db
    from odoo.service import db as odoo_db
    from odoo.tools import SQL

    # ---- ขั้นที่ 1: เลือกไฟล์สำรองล่าสุด ----
    backup_path = _newest_backup(args.folder)
    if not backup_path:
        print(f"ERROR: ไม่พบไฟล์สำรองใน {args.folder}")
        return 1

    digest, size = _sha256_and_size(backup_path)
    print(f"backup file : {os.path.basename(backup_path)}")
    print(f"size bytes  : {size}")
    print(f"sha256      : {digest}")

    # ---- ขั้นที่ 2: ตรวจเทียบกับ manifest ----
    manifest_path = os.path.join(args.folder, "backup-manifest.jsonl")
    recorded = None
    for entry in reversed(_manifest_entries(manifest_path)):
        if entry.get("file") == os.path.basename(backup_path):
            recorded = entry
            break

    if recorded:
        same_hash = recorded.get("sha256") == digest
        same_size = int(recorded.get("size_bytes", -1)) == size
        if same_hash and same_size:
            print("checksum    : OK (ตรงกับ manifest)")
        else:
            print("ERROR: checksum/size ไม่ตรงกับ manifest")
            print(f"       manifest sha256={recorded.get('sha256')} size={recorded.get('size_bytes')}")
            return 1
    else:
        print("checksum    : ไม่พบบันทึกใน manifest (ข้ามการเทียบ)")

    # ---- ขั้นที่ 3-5: กู้คืนจริงลง DB ชั่วคราว แล้วตรวจสอบ ----
    temp = args.temp_db
    try:
        if odoo_db.exp_db_exist(temp):
            print(f"temp db     : {temp} มีอยู่แล้ว -> ลบทิ้งก่อน")
            odoo_db.exp_drop(temp)

        print(f"restore     : กำลังกู้คืนลง {temp} ...")
        odoo_db.restore_db(temp, backup_path, copy=True)
        print("restore     : สำเร็จ")

        print("verify      : ตรวจตารางหลัก")
        conn = odoo.sql_db.db_connect(temp)
        failed = []
        with conn.cursor() as cr:
            for table, min_rows in REQUIRED_TABLES.items():
                try:
                    cr.execute(SQL("SELECT count(*) FROM %s", SQL.identifier(table)))
                    count = cr.fetchone()[0]
                except Exception as exc:  # noqa: BLE001
                    print(f"  [FAIL] {table}: {exc}")
                    failed.append(table)
                    cr.rollback()
                    continue
                ok = count >= min_rows and count > 0
                print(f"  [{'OK' if ok else 'FAIL'}] {table}: {count} rows")
                if not ok:
                    failed.append(table)

        if failed:
            print(f"ERROR: ตารางที่ไม่ผ่าน: {', '.join(failed)}")
            return 1

        print("VERIFY RESULT: PASS")
        return 0
    finally:
        try:
            odoo.sql_db.close_db(temp)
        except Exception:  # noqa: BLE001
            pass
        try:
            if odoo_db.exp_db_exist(temp):
                odoo_db.exp_drop(temp)
                print(f"cleanup     : ลบ {temp} แล้ว")
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: ลบ temp db ไม่สำเร็จ: {exc}")


if __name__ == "__main__":
    sys.exit(main())
