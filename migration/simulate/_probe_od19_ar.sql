\pset pager off
\echo '=== account_account code columns ==='
SELECT column_name FROM information_schema.columns
WHERE table_name='account_account' AND (column_name LIKE '%code%' OR column_name LIKE '%type%') ORDER BY column_name;

\echo '=== odoo19_pdev: moves by type/state ==='
SELECT move_type, state, count(*) FROM account_move GROUP BY 1,2 ORDER BY 1,2;

\echo '=== odoo19_pdev: AR/AP balance total ==='
SELECT aa.account_type, round(sum(l.balance),2) AS bal, count(*) AS lines
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id
WHERE m.state='posted' AND aa.account_type IN ('asset_receivable','liability_payable')
GROUP BY 1;

\echo '=== odoo19_pdev: receivable account list ==='
SELECT id, account_type FROM account_account WHERE account_type='asset_receivable';

\echo '=== odoo19_pdev: total partners ==='
SELECT count(*) FROM res_partner;
