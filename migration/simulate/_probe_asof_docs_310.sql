\pset pager off

\echo '=== od15_stage: as-of 2026-10-31 — real docs residual<>0 by move_type ==='
WITH res AS (
  SELECT m.id AS move_id, m.move_type, m.partner_id,
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
  GROUP BY m.id, m.move_type, m.partner_id
)
SELECT r.move_type, count(*) AS docs, count(DISTINCT r.partner_id) AS partners,
       round(sum(r.resid)::numeric,2) AS resid
FROM res r WHERE round(r.resid::numeric,2) <> 0
GROUP BY r.move_type ORDER BY 1;

\echo '=== od15_stage: as-of 2026-10-31 — AR documents (residual<>0) ==='
WITH res AS (
  SELECT m.id AS move_id, m.name, m.date, m.move_type, m.partner_id,
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
    AND t.type='receivable'
    AND m.move_type IN ('out_invoice','out_refund')
  GROUP BY m.id, m.name, m.date, m.move_type, m.partner_id
)
SELECT count(*) AS docs, round(sum(resid)::numeric,2) AS total
FROM res WHERE round(resid::numeric,2) <> 0;

\echo '=== od15_stage: as-of 2026-10-31 — AP documents (residual<>0) ==='
WITH res AS (
  SELECT m.id AS move_id, m.name, m.date, m.move_type, m.partner_id,
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
    AND t.type='payable'
    AND m.move_type IN ('in_invoice','in_refund')
  GROUP BY m.id, m.name, m.date, m.move_type, m.partner_id
)
SELECT count(*) AS docs, round(sum(resid)::numeric,2) AS total
FROM res WHERE round(resid::numeric,2) <> 0;
