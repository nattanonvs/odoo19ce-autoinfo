\pset pager off
\echo '=== od15: opening JE lines at 2026-01-01 (AR/AP) ==='
SELECT m.name, m.date, m.ref, a.code, t.type AS atype,
       count(*) AS lines, round(sum(l.balance),2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
JOIN account_account_type t ON t.id=a.user_type_id
WHERE m.date = DATE '2026-01-01' AND t.type IN ('receivable','payable')
GROUP BY m.name, m.date, m.ref, a.code, t.type
ORDER BY t.type, a.code;

\echo '=== od15: columns of account_partial_reconcile ==='
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name='account_partial_reconcile'
ORDER BY ordinal_position;

\echo '=== od15: AR/AP residual AS OF 2026-01-01 (by account) ==='
SELECT a.code, t.type AS atype,
       count(*) AS lines, count(DISTINCT l.partner_id) AS partners,
       round(sum(
           l.balance
           + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id=p.debit_move_id
                       JOIN account_move cm ON cm.id=cl.move_id
                       WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
           - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id=p.credit_move_id
                       JOIN account_move cm ON cm.id=cl.move_id
                       WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
       )::numeric, 2) AS resid
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
JOIN account_account_type t ON t.id=a.user_type_id
WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
  AND t.type IN ('receivable','payable')
GROUP BY a.code, t.type
HAVING round(sum(
           l.balance
           + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id=p.debit_move_id
                       JOIN account_move cm ON cm.id=cl.move_id
                       WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
           - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id=p.credit_move_id
                       JOIN account_move cm ON cm.id=cl.move_id
                       WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
       )::numeric, 2) <> 0
ORDER BY t.type, a.code;

\echo '=== od15: real docs with residual<>0 AS OF 2026-01-01 (by year/type) ==='
SELECT to_char(m.date,'YYYY') AS yr, m.move_type,
       count(*) AS docs, count(DISTINCT l.partner_id) AS partners,
       round(sum(
           l.balance
           + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id=p.debit_move_id
                       JOIN account_move cm ON cm.id=cl.move_id
                       WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
           - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id=p.credit_move_id
                       JOIN account_move cm ON cm.id=cl.move_id
                       WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
       )::numeric, 2) AS resid
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
JOIN account_account_type t ON t.id=a.user_type_id
WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
  AND t.type IN ('receivable','payable')
  AND m.move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
GROUP BY 1,2
HAVING round(sum(
           l.balance
           + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id=p.debit_move_id
                       JOIN account_move cm ON cm.id=cl.move_id
                       WHERE p.credit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
           - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id=p.credit_move_id
                       JOIN account_move cm ON cm.id=cl.move_id
                       WHERE p.debit_move_id=l.id AND cm.date <= DATE '2026-01-01'),0)
       )::numeric, 2) <> 0
ORDER BY 1,2;
