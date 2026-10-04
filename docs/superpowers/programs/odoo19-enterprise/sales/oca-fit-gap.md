# Sales OCA Fit-Gap

## Required Now Baseline
| Module | Source | Adoption Mode | Why |
| --- | --- | --- | --- |
| `base_user_role` | OCA/server-backend | Required now | ใช้แยกบทบาท Sales / Billing / Manager ให้ชัด |
| `sale_order_revision` | OCA/sale-workflow + OCA/server-ux | Required now | ใช้ revision history ของ quotation / order โดยต้องมี `base_revision` |
| `sale_delivery_state` | OCA/sale-workflow | Required now | ใช้สถานะส่งมอบระหว่างทางก่อนถึง billing readiness |
| `sale_exception` | OCA/sale-workflow + OCA/server-tools | Required now via bridge | ใช้ exception / approval rule โดยต้องมี `base_exception` |
| `sale_blanket_order` | OCA/sale-blanket | Required now via bridge | ใช้เป็นฐานเอกสารเชิงพาณิชย์ของ contract-based sale |

## Deferred Pending Confirmation
| Module | Source | Current Decision | Why Deferred |
| --- | --- | --- | --- |
| `sale_tier_validation` | OCA/sale-workflow + OCA/server-ux | Deferred pending 19.0 confirmation | รอ confirm 19.0 baseline และ `base_tier_validation` |
| `sale_invoice_plan` | OCA/sale-workflow | Deferred pending 19.0 confirmation | รอ confirm 19.0 baseline |

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
