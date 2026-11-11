\pset pager off
\echo '=== od15: AP accounts (payable) ==='
SELECT aa.code, aa.name, t.type, count(*) AS lines
FROM account_move_line l
JOIN account_account aa ON aa.id=l.account_id
JOIN account_account_type t ON t.id=aa.user_type_id
WHERE t.type='payable'
GROUP BY aa.code, aa.name, t.type ORDER BY aa.code;

\echo '=== od15: cumulative AP balance as of dates ==='
SELECT '2024-12-31' AS asof, round(sum(l.balance),2) AS ap_bal, count(*) AS lines FROM account_move_line l JOIN account_move m ON m.id=l.move_id JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id WHERE m.state='posted' AND t.type='payable' AND m.date<='2024-12-31'
UNION ALL SELECT '2025-06-30', round(sum(l.balance),2), count(*) FROM account_move_line l JOIN account_move m ON m.id=l.move_id JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id WHERE m.state='posted' AND t.type='payable' AND m.date<='2025-06-30'
UNION ALL SELECT '2025-12-31', round(sum(l.balance),2), count(*) FROM account_move_line l JOIN account_move m ON m.id=l.move_id JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id WHERE m.state='posted' AND t.type='payable' AND m.date<='2025-12-31'
UNION ALL SELECT '2026-10-31', round(sum(l.balance),2), count(*) FROM account_move_line l JOIN account_move m ON m.id=l.move_id JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id WHERE m.state='posted' AND t.type='payable' AND m.date<='2026-10-31'
UNION ALL SELECT 'ALL', round(sum(l.balance),2), count(*) FROM account_move_line l JOIN account_move m ON m.id=l.move_id JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id WHERE m.state='posted' AND t.type='payable';

\echo '=== od15: outstanding AP by move-date year (residual<>0) ==='
SELECT to_char(m.date,'YYYY') AS yr, m.move_type, count(*) AS lines,
       round(sum(l.amount_residual),2) AS residual
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='payable' AND round(l.amount_residual,2)<>0
GROUP BY 1,2 ORDER BY 1,2;

\echo '=== od15: in_invoice counts per year ==='
SELECT to_char(m.date,'YYYY') AS yr, count(*) AS bills, count(DISTINCT m.partner_id) AS partners,
       round(sum(m.amount_total),2) AS total, round(sum(m.amount_residual_signed),2) AS resid
FROM account_move m WHERE m.state='posted' AND m.move_type IN ('in_invoice','in_refund')
GROUP BY 1 ORDER BY 1;

\echo '=== od15: AP ยอดยกมา entries ==='
SELECT to_char(m.date,'YYYY') AS yr, m.name, round(sum(l.balance),2) AS amt, count(*) AS lines
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE t.type='payable' AND l.name='ยอดยกมา' GROUP BY 1,2 ORDER BY 1;
