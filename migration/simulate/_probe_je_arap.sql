\pset pager off

\echo '=== JE (entry) moves with AR/AP residual as-of 2026-01-01 : by journal ==='
WITH res AS (
  SELECT m.id AS move_id, m.journal_id, m.move_type, m.partner_id,
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
    AND m.move_type='entry'
  GROUP BY m.id, m.journal_id, m.move_type, m.partner_id
)
SELECT j.code, j.type AS jtype, count(*) AS moves, count(DISTINCT r.partner_id) AS partners,
       round(sum(r.resid)::numeric,2) AS resid
FROM res r JOIN account_journal j ON j.id=r.journal_id
WHERE round(r.resid::numeric,2) <> 0
GROUP BY 1,2 ORDER BY abs(round(sum(r.resid)::numeric,2)) DESC;

\echo '=== JE (entry): partner ผูกหรือไม่ (AR+AP) ==='
WITH res AS (
  SELECT m.id AS move_id, m.partner_id, a.code AS acode,
         sum(l.balance) AS resid
  FROM account_move_line l
  JOIN account_move m ON m.id=l.move_id
  JOIN account_account a ON a.id=l.account_id
  JOIN account_account_type t ON t.id=a.user_type_id
  WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
    AND t.type IN ('receivable','payable') AND m.move_type='entry'
  GROUP BY m.id, m.partner_id, a.code
)
SELECT (partner_id IS NULL) AS no_partner, count(*) AS lines,
       round(sum(resid)::numeric,2) AS resid
FROM res GROUP BY 1 ORDER BY 1;

\echo '=== JE (entry): 15 ใบใหญ่สุด (AR/AP resid) ==='
WITH res AS (
  SELECT m.id AS move_id, m.name, m.date, m.ref, m.partner_id, m.journal_id,
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
    AND t.type IN ('receivable','payable') AND m.move_type='entry'
  GROUP BY m.id, m.name, m.date, m.ref, m.partner_id, m.journal_id
)
SELECT r.name, r.date, j.code, r.partner_id, r.ref, round(r.resid::numeric,2) AS resid
FROM res r JOIN account_journal j ON j.id=r.journal_id
WHERE round(r.resid::numeric,2) <> 0
ORDER BY abs(r.resid) DESC LIMIT 15;

\echo '=== as-of 2026-01-01: lines ที่กลับรายการ (+209,720?) — move name/label ==='
SELECT m.name, m.date, m.move_type, m.ref, a.code,
       round(sum(l.balance)::numeric,2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
JOIN account_account_type t ON t.id=a.user_type_id
WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
  AND t.type IN ('receivable','payable')
  AND abs(l.balance) = 209720
GROUP BY 1,2,3,4,5 ORDER BY 2;
