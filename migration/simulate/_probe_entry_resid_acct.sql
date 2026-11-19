\pset pager off

\echo '=== entry-type residual<>0 by (partner, account, type) ==='
WITH res AS (
  SELECT l.partner_id, a.code AS account_code, t.type AS atype,
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
  GROUP BY 1,2,3
)
SELECT atype, account_code, count(*) AS rows, round(sum(resid)::numeric,2) AS resid
FROM res WHERE round(resid::numeric,2)<>0
GROUP BY 1,2 ORDER BY 1,2;

\echo '=== entry-type residual: totals + partner count ==='
WITH res AS (
  SELECT l.partner_id, t.type AS atype,
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
SELECT atype, count(*) AS partners, round(sum(resid)::numeric,2) AS resid
FROM res WHERE round(resid::numeric,2)<>0 GROUP BY 1;

\echo '=== entry-type: partners with BOTH receivable and payable residual ==='
WITH res AS (
  SELECT l.partner_id, t.type AS atype,
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
SELECT partner_id, count(DISTINCT atype) AS ntypes
FROM res WHERE round(resid::numeric,2)<>0
GROUP BY 1 HAVING count(DISTINCT atype)>1;
