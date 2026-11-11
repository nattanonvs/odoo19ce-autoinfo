\pset pager off

\echo '=== A) GL balance as-of 2026-10-31 (วิธีที่ s08 ใช้) — by type ==='
SELECT t.type, round(sum(l.balance)::numeric,2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
JOIN account_account_type t ON t.id=a.user_type_id
WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
  AND t.type IN ('receivable','payable')
GROUP BY 1 ORDER BY 1;

\echo '=== B) residual as-of 2026-10-31 — by type (all move_type) ==='
WITH res AS (
  SELECT l.id, t.type,
         l.debit - l.credit
         + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                     JOIN account_move_line cl ON cl.id=p.debit_move_id
                     JOIN account_move cm ON cm.id=cl.move_id
                     WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-10-31'),0)
         - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                     JOIN account_move_line cl ON cl.id=p.credit_move_id
                     JOIN account_move cm ON cm.id=cl.move_id
                     WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-10-31'),0) AS resid
  FROM account_move_line l
  JOIN account_move m ON m.id=l.move_id
  JOIN account_account a ON a.id=l.account_id
  JOIN account_account_type t ON t.id=a.user_type_id
  WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
    AND t.type IN ('receivable','payable')
)
SELECT type, round(sum(resid)::numeric,2) AS resid FROM res GROUP BY 1 ORDER BY 1;

\echo '=== C) current amount_residual (ไม่จำกัดวันที่) — by type ==='
SELECT t.type, round(sum(l.amount_residual)::numeric,2) AS resid
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
JOIN account_account_type t ON t.id=a.user_type_id
WHERE m.state='posted' AND t.type IN ('receivable','payable')
GROUP BY 1 ORDER BY 1;

\echo '=== D) GL balance as-of 2026-10-31 — by (type,move_type) ==='
SELECT t.type, m.move_type, round(sum(l.balance)::numeric,2) AS bal, count(*) n
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
JOIN account_account_type t ON t.id=a.user_type_id
WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
  AND t.type IN ('receivable','payable')
GROUP BY 1,2 ORDER BY 1,2;

\echo '=== E) GL balance per account code as-of 2026-10-31 ==='
SELECT a.code, t.type, round(sum(l.balance)::numeric,2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
JOIN account_account_type t ON t.id=a.user_type_id
WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
  AND t.type IN ('receivable','payable')
GROUP BY 1,2 HAVING round(sum(l.balance)::numeric,2) <> 0 ORDER BY 1;
