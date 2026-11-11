\pset pager off

\echo '=== od15_stage: GL AR/AP balance ณ 2026-01-01 (per account) ==='
SELECT a.code, a.name, aa.type AS atype,
       round(sum(l.debit - l.credit)::numeric, 2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
JOIN account_account_type aa ON aa.id = a.user_type_id
WHERE m.state = 'posted' AND m.date <= DATE '2026-01-01'
  AND aa.type IN ('receivable', 'payable')
GROUP BY a.code, a.name, aa.type
ORDER BY a.code;

\echo '=== od15_stage: GL AR/AP balance ณ 2026-01-01 (totals by type) ==='
SELECT aa.type AS atype, round(sum(l.debit - l.credit)::numeric, 2) AS bal, count(*) AS n
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
JOIN account_account_type aa ON aa.id = a.user_type_id
WHERE m.state = 'posted' AND m.date <= DATE '2026-01-01'
  AND aa.type IN ('receivable', 'payable')
GROUP BY aa.type ORDER BY aa.type;

\echo '=== od15_stage: AR/AP ณ 2026-01-01 แยกตาม move_type ==='
SELECT m.move_type, aa.type AS atype,
       round(sum(l.debit - l.credit)::numeric, 2) AS bal, count(*) AS n
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
JOIN account_account_type aa ON aa.id = a.user_type_id
WHERE m.state = 'posted' AND m.date <= DATE '2026-01-01'
  AND aa.type IN ('receivable', 'payable')
GROUP BY m.move_type, aa.type ORDER BY aa.type, m.move_type;

\echo '=== od15_stage: รายการ AR/AP ที่ลงวันที่ 2026-01-01 (reversal) ==='
SELECT m.name, m.date, aa.type AS atype, a.code,
       round(sum(l.debit - l.credit)::numeric, 2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
JOIN account_account_type aa ON aa.id = a.user_type_id
WHERE m.state = 'posted' AND m.date = DATE '2026-01-01'
  AND aa.type IN ('receivable', 'payable')
GROUP BY m.name, m.date, aa.type, a.code
ORDER BY m.name, a.code;
