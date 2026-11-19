\pset pager off
\echo '=== AR outstanding (residual<>0) summary ==='
SELECT count(*) AS lines, count(DISTINCT l.partner_id) AS partners, round(sum(l.amount_residual),2) AS total
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='receivable' AND round(l.amount_residual,2)<>0;

\echo '=== AR outstanding by year & move_type ==='
SELECT to_char(m.date,'YYYY') yr, m.move_type, count(*) lines, count(DISTINCT l.partner_id) partners, round(sum(l.amount_residual),2) total
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='receivable' AND round(l.amount_residual,2)<>0
GROUP BY 1,2 ORDER BY 1,2;

\echo '=== AR outstanding from real invoices only (out_invoice/out_refund) ==='
SELECT to_char(m.date,'YYYY') yr, count(*) invoices, count(DISTINCT l.partner_id) partners, round(sum(l.amount_residual),2) total
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='receivable' AND m.move_type IN ('out_invoice','out_refund') AND round(l.amount_residual,2)<>0
GROUP BY 1 ORDER BY 1;

\echo '=== AP outstanding (residual<>0) summary ==='
SELECT count(*) AS lines, count(DISTINCT l.partner_id) AS partners, round(sum(l.amount_residual),2) AS total
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='payable' AND round(l.amount_residual,2)<>0;

\echo '=== AP outstanding from real bills only (in_invoice/in_refund) ==='
SELECT to_char(m.date,'YYYY') yr, count(*) bills, count(DISTINCT l.partner_id) partners, round(sum(l.amount_residual),2) total
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='payable' AND m.move_type IN ('in_invoice','in_refund') AND round(l.amount_residual,2)<>0
GROUP BY 1 ORDER BY 1;

\echo '=== sample: outstanding AR real invoices (latest 10) ==='
SELECT m.name, m.date, m.move_type, l.partner_id, round(l.amount_residual,2) AS resid
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='receivable' AND m.move_type IN ('out_invoice','out_refund') AND round(l.amount_residual,2)<>0
ORDER BY m.date DESC LIMIT 10;

\echo '=== sample: outstanding AP real bills (latest 10) ==='
SELECT m.name, m.date, m.move_type, l.partner_id, round(l.amount_residual,2) AS resid
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='payable' AND m.move_type IN ('in_invoice','in_refund') AND round(l.amount_residual,2)<>0
ORDER BY m.date DESC LIMIT 10;
