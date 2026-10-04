# Sales OCA Fit-Gap

## Candidate Modules
| Module | Source | Decision | Why |
| --- | --- | --- | --- |
| `base_user_role` | OCA/server-backend | Adopt | ใช้แยกบทบาท Sales / Billing / Manager ให้ชัด |
| `sale_tier_validation` | OCA/sale-workflow + OCA/server-ux | Deferred | รอ confirm 19.0 baseline และ `base_tier_validation` |
| `sale_order_revision` | OCA/sale-workflow + OCA/server-ux | Adopt | ใช้ revision history ของ quotation / order โดยต้องมี `base_revision` |
| `sale_delivery_state` | OCA/sale-workflow | Adopt | ใช้สถานะส่งมอบระหว่างทางก่อนถึง billing readiness |
| `sale_invoice_plan` | OCA/sale-workflow | Deferred | รอ confirm 19.0 baseline |
| `sale_exception` | OCA/sale-workflow + OCA/server-tools | Adopt via bridge | ใช้ exception / approval rule โดยต้องมี `base_exception` |
| `sale_blanket_order` | OCA/sale-blanket | Adopt via bridge | ใช้เป็นฐานเอกสารเชิงพาณิชย์ของ contract-based sale |

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
