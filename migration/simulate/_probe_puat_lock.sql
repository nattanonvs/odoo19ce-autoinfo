\pset pager off

\echo '=== odoo19_puat: company lock dates ==='
SELECT id, name, fiscalyear_lock_date, tax_lock_date, hard_lock_date
FROM res_company ORDER BY id;

\echo '=== odoo19_puat: account_journal columns ==='
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name='account_journal' AND column_name IN ('code','code_store','type','name')
ORDER BY column_name;

\echo '=== odoo19_puat: journals ==='
SELECT id, code, type,
       (SELECT string_agg(value,'/') FROM jsonb_each_text(name)) AS name
FROM account_journal
WHERE code IN ('INV','BILL','BRF','EXP')
ORDER BY id;
