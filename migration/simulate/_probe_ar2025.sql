\pset pager off
\echo '=== min/max posted move dates ==='
SELECT min(date) AS min_d, max(date) AS max_d, count(*) AS moves FROM account_move WHERE state='posted';

\echo '=== AR accounts used (receivable) ==='
SELECT aa.code, aa.name, t.type, count(*) AS lines
FROM account_move_line l
JOIN account_account aa ON aa.id=l.account_id
JOIN account_account_type t ON t.id=aa.user_type_id
WHERE t.type='receivable'
GROUP BY aa.code, aa.name, t.type ORDER BY aa.code;

\echo '=== outstanding AR by move-date year (amount_residual<>0) ==='
SELECT to_char(m.date,'YYYY') AS yr, m.move_type, count(*) AS lines,
       round(sum(l.amount_residual),2) AS residual
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id
JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='receivable' AND round(l.amount_residual,2)<>0
GROUP BY 1,2 ORDER BY 1,2;

\echo '=== net AR balance (all AR lines) by year ==='
SELECT to_char(m.date,'YYYY') AS yr, round(sum(l.balance),2) AS net_balance, count(*) AS lines
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id
JOIN account_account_type t ON t.id=aa.user_type_id
WHERE m.state='posted' AND t.type='receivable'
GROUP BY 1 ORDER BY 1;
