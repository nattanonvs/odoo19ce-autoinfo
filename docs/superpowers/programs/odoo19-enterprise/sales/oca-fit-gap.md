# Sales OCA Fit-Gap

## Candidate Modules
| Module | Source | Decision | Why |
| --- | --- | --- | --- |
| `base_user_role` | OCA/server-backend | Adopt | ใช้แยกบทบาท Sales / Billing / Manager ให้ชัด |
| `sale_tier_validation` | OCA/sale-workflow | Adopt | ใช้ approval หลายชั้นแทน custom approval flow |
| `sale_order_revision` | OCA/sale-workflow | Adopt | เก็บ revision history ของ quotation / order |
| `sale_delivery_status` | OCA/sale-workflow | Adopt | ใช้สถานะส่งมอบระหว่างทางก่อนถึง billing readiness |
| `sale_invoice_plan` | OCA/sale-workflow | Adopt via bridge | เปิดใช้เฉพาะดีลที่ตั้ง `od19_invoice_plan_mode = schedule` |
| `sale_blanket_order` | OCA/sale-workflow | Adopt via bridge | ใช้เป็นฐานเอกสารเชิงพาณิชย์ของ contract-based sale โดยให้ custom contract model คุม policy |

## Custom Layers Still Needed
- `od19_sales_project_context` สำหรับผู้รับเหมา เจ้าของโครงการ และโครงการ
- `od19_sales_contract_core` สำหรับ master contract, amendment, activity, policy
- `od19_sales_billing_evidence` สำหรับ evidence, attachment rules, billing readiness
- `od19_sales_reporting` สำหรับ repeat-business และ project revenue views
- `od19_sales_oca_bridge_workflow` สำหรับ wiring กับ OCA modules แบบ optional

## Rejected for Wave 1
- custom approval engine ใหม่ทั้งหมด
- custom revision engine ใหม่ทั้งหมด
- custom delivery status ใหม่ทั้งหมด
