# Environment and Delivery Baseline

## Environment Model
- Local Dev
- Shared Dev / Integration
- Test / QA
- UAT / Training
- Production

## Access Expectations
- ใครเข้าได้
- ใช้ข้อมูลประเภทไหน
- เปลี่ยนแปลงผ่านใคร

## Delivery Baseline
- merge ต้องผ่าน lint/tests/review
- deploy ต้องมี release note และ rollback expectation
- ห้ามใช้ production เป็นที่ทดลอง

## Minimum Quality Gates
- lint
- automated tests
- install/uninstall checks
- security review
- upgrade note
