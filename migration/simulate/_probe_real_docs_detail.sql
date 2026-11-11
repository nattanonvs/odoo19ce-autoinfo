\pset pager off

-- ชุดเอกสารจริง (out_invoice/out_refund/in_invoice/in_refund) ณ 2026-10-31 แบบ residual<>0
-- จัดกลุ่มต่อ (move, account, partner)
CREATE TEMP VIEW real_docs AS
SELECT m.id AS move_id, m.name, m.date, m.move_type, m.partner_id,
       a.code AS account_code, a.id AS account_id,
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
GROUP BY 1,2,3,4,5,6,7;

\echo '=== summary by move_type ==='
SELECT move_type, count(*) AS rows, count(DISTINCT move_id) AS moves,
       round(sum(resid)::numeric,2) AS resid
FROM real_docs WHERE round(resid::numeric,2)<>0 GROUP BY 1 ORDER BY 1;

\echo '=== moves that split across >1 AR/AP account (rows>1) ==='
SELECT move_id, name, count(*) AS rows
FROM real_docs WHERE round(resid::numeric,2)<>0
GROUP BY 1,2 HAVING count(*)>1 ORDER BY 3 DESC LIMIT 20;

\echo '=== real docs with NULL partner ==='
SELECT count(*) AS rows_null_partner, round(sum(resid)::numeric,2) AS resid
FROM real_docs WHERE round(resid::numeric,2)<>0 AND partner_id IS NULL;

\echo '=== per account code (real docs) ==='
SELECT account_code, count(*) AS rows, round(sum(resid)::numeric,2) AS resid
FROM real_docs WHERE round(resid::numeric,2)<>0 GROUP BY 1 ORDER BY 1;

\echo '=== duplicate names among real docs? ==='
SELECT name, count(*) FROM real_docs WHERE round(resid::numeric,2)<>0
GROUP BY 1 HAVING count(*)>1 ORDER BY 2 DESC LIMIT 10;
