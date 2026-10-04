# Sales Addon Boundaries

## `od19_sales_project_context`
- เก็บ `Commercial Customer`, `Project Owner`, `Project`
- ผูก context นี้เข้ากับ `sale.order`

## `od19_sales_contract_core`
- เก็บ `Master Contract`, `Contract Amendment`, `Contract Activity`
- เก็บ contract policy เช่น limit mode, over-limit mode, billing cycle

## `od19_sales_billing_evidence`
- เก็บ evidence types, evidence records, required attachment rules
- คำนวณ `billing_readiness_state`

## `od19_sales_reporting`
- ให้ report SQL views สำหรับ repeat business และ project revenue

## `od19_sales_oca_bridge_workflow`
- wire กับ `sale_tier_validation`
- wire กับ `sale_order_revision`
- wire กับ `sale_delivery_status`
- wire กับ `sale_invoice_plan`
- wire กับ `sale_blanket_order`
