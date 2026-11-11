\pset pager off
SELECT '2024-12-31' AS asof, round(sum(l.balance),2) AS ar_bal, count(*) AS lines FROM account_move_line l JOIN account_move m ON m.id=l.move_id JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id WHERE m.state='posted' AND t.type='receivable' AND m.date<='2024-12-31'
UNION ALL SELECT '2025-12-31', round(sum(l.balance),2), count(*) FROM account_move_line l JOIN account_move m ON m.id=l.move_id JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id WHERE m.state='posted' AND t.type='receivable' AND m.date<='2025-12-31'
UNION ALL SELECT 'ALL', round(sum(l.balance),2), count(*) FROM account_move_line l JOIN account_move m ON m.id=l.move_id JOIN account_account aa ON aa.id=l.account_id JOIN account_account_type t ON t.id=aa.user_type_id WHERE m.state='posted' AND t.type='receivable';

SELECT min(date) AS min_d, max(date) AS max_d, count(*) FROM account_move WHERE state='posted';

SELECT to_char(m.date,'YYYY') AS yr, count(*) AS inv, round(sum(m.amount_total),2) AS total
FROM account_move m WHERE m.state='posted' AND m.move_type IN ('out_invoice','out_refund') GROUP BY 1 ORDER BY 1;
