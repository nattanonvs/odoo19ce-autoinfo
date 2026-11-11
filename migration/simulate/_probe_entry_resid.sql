\pset pager off

\echo '=== entry-type RECEIVABLE residual<>0 — by partner ==='
WITH res AS (
  SELECT l.partner_id, l.id,
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
    AND t.type='receivable' AND m.move_type='entry'
)
SELECT partner_id, count(*) n, round(sum(resid)::numeric,2) AS resid
FROM res WHERE round(resid::numeric,2) <> 0
GROUP BY 1 ORDER BY 3;

\echo '=== entry-type PAYABLE residual<>0 — by partner ==='
WITH res AS (
  SELECT l.partner_id, l.id,
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
    AND t.type='payable' AND m.move_type='entry'
)
SELECT partner_id, count(*) n, round(sum(resid)::numeric,2) AS resid
FROM res WHERE round(resid::numeric,2) <> 0
GROUP BY 1 ORDER BY 3;

\echo '=== ARM real invoices: count + resid named sample (2026 only, top 5 by resid) ==='
WITH res AS (
  SELECT l.id, m.id AS move_id, m.name, m.date, m.move_type, l.partner_id,
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
    AND t.type='receivable' AND m.move_type IN ('out_invoice','out_refund')
)
SELECT name, date, move_type, partner_id, round(resid::numeric,2) AS resid
FROM res WHERE round(resid::numeric,2) <> 0
ORDER BY resid DESC LIMIT 5;
