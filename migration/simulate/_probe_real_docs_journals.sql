\pset pager off

\echo '=== od15 real docs (residual<>0 @2026-10-31): journals used ==='
WITH res AS (
  SELECT m.id AS move_id, m.move_type, m.journal_id,
         sum(l.debit - l.credit
             + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.debit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-10-31'),0)
             - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.credit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-10-31'),0)
         ) AS resid
  FROM account_move_line l
  JOIN account_move m ON m.id=l.move_id
  JOIN account_account a ON a.id=l.account_id
  JOIN account_account_type t ON t.id=a.user_type_id
  WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
    AND t.type IN ('receivable','payable')
    AND m.move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
  GROUP BY 1,2,3
)
SELECT m.move_type, j.code AS journal_code, j.type AS journal_type,
       count(DISTINCT r.move_id) AS moves, round(sum(r.resid)::numeric,2) AS resid
FROM (SELECT * FROM res WHERE round(resid::numeric,2)<>0) r
JOIN account_move m ON m.id=r.move_id
JOIN account_journal j ON j.id=m.journal_id
GROUP BY 1,2,3 ORDER BY 1,4 DESC;

\echo '=== od15 entry residual<>0: journals used ==='
WITH res AS (
  SELECT m.id AS move_id, m.journal_id,
         sum(l.debit - l.credit
             + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.debit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-10-31'),0)
             - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.credit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-10-31'),0)
         ) AS resid
  FROM account_move_line l
  JOIN account_move m ON m.id=l.move_id
  JOIN account_account a ON a.id=l.account_id
  JOIN account_account_type t ON t.id=a.user_type_id
  WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
    AND t.type IN ('receivable','payable') AND m.move_type='entry'
  GROUP BY 1,2
)
SELECT j.code AS journal_code, j.type AS journal_type,
       count(DISTINCT r.move_id) AS moves, round(sum(r.resid)::numeric,2) AS resid
FROM (SELECT * FROM res WHERE round(resid::numeric,2)<>0) r
JOIN account_move m ON m.id=r.move_id
JOIN account_journal j ON j.id=m.journal_id
GROUP BY 1,2 ORDER BY 1;

\echo '=== od15 real docs: date range ==='
SELECT m.move_type, min(m.date) AS dmin, max(m.date) AS dmax,
       count(*) AS moves
FROM account_move m
WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
  AND m.move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
GROUP BY 1 ORDER BY 1;
