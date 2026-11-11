\pset pager off
\echo '=== as-of 2026-01-01: real docs with residual<>0 (per document) ==='
WITH res AS (
  SELECT m.id AS move_id, m.move_type, m.partner_id,
         sum(l.balance
             + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.debit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
             - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.credit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
         ) AS resid
  FROM account_move_line l
  JOIN account_move m ON m.id=l.move_id
  JOIN account_account a ON a.id=l.account_id
  JOIN account_account_type t ON t.id=a.user_type_id
  WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
    AND t.type IN ('receivable','payable')
  GROUP BY m.id, m.move_type, m.partner_id
)
SELECT r.move_type, count(*) AS docs, count(DISTINCT r.partner_id) AS partners,
       round(sum(r.resid)::numeric,2) AS resid
FROM res r
WHERE round(r.resid::numeric,2) <> 0
GROUP BY r.move_type ORDER BY 1;

\echo '=== as-of 2026-01-01: ALL residual lines (incl. JE) by move_type ==='
WITH res AS (
  SELECT m.id AS move_id, m.move_type,
         sum(l.balance
             + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.debit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
             - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.credit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
         ) AS resid
  FROM account_move_line l
  JOIN account_move m ON m.id=l.move_id
  JOIN account_account a ON a.id=l.account_id
  JOIN account_account_type t ON t.id=a.user_type_id
  WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
    AND t.type IN ('receivable','payable')
  GROUP BY m.id, m.move_type
)
SELECT r.move_type, count(*) AS moves, round(sum(r.resid)::numeric,2) AS resid
FROM res r
WHERE round(r.resid::numeric,2) <> 0
GROUP BY r.move_type ORDER BY 1;

\echo '=== as-of 2026-01-01: sample 12 AR real invoices (largest) ==='
WITH res AS (
  SELECT m.id AS move_id, m.name, m.date, m.move_type, m.partner_id, m.currency_id,
         sum(l.balance
             + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.debit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
             - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                         JOIN account_move_line cl ON cl.id=p.credit_move_id
                         JOIN account_move cm ON cm.id=cl.move_id
                         WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
         ) AS resid
  FROM account_move_line l
  JOIN account_move m ON m.id=l.move_id
  JOIN account_account a ON a.id=l.account_id
  JOIN account_account_type t ON t.id=a.user_type_id
  WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
    AND t.type IN ('receivable','payable')
    AND m.move_type IN ('out_invoice','out_refund')
  GROUP BY m.id, m.name, m.date, m.move_type, m.partner_id, m.currency_id
)
SELECT r.name, r.date, r.move_type, r.partner_id, round(r.resid::numeric,2) AS resid
FROM res r WHERE round(r.resid::numeric,2) <> 0
ORDER BY abs(r.resid) DESC LIMIT 12;
