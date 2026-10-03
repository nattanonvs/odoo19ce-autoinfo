# Repository and Addon Baseline

## Purpose
- กำหนดว่าของแต่ละประเภทต้องอยู่ตรงไหน
- กันการปนกันระหว่าง docs, addons, deployment, tests, migrations

## Repository Layout Rules
- `docs/` เก็บ specs, plans, governance, reporting artifacts
- `custom_addons/` เก็บ company-specific addons
- `third_party/oca/` เก็บ OCA addons ที่เลือกใช้
- `deployment/` เก็บ config, compose, service, release notes
- `tests/` หรือ test paths ตาม addon สำหรับ automation

## Addon Boundary Rules
- หนึ่ง addon มีหน้าที่หลักหนึ่งเรื่อง
- dependency ต้องประกาศใน manifest เท่านั้น
- ห้าม hidden coupling
- ต้อง install, upgrade, uninstall ได้

## Naming Rules
- addon ใช้ prefix เดียวกันตาม program
- model, field, security group, data xml id ต้องสื่อความหมายและ trace กลับ spec ได้
