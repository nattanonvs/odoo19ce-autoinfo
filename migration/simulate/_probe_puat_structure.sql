\pset pager off

\echo '=== ir_model_data: module ที่มีอยู่ (ดูว่ามี __import15__ ไหม) ==='
SELECT module, count(*) AS n FROM ir_model_data GROUP BY module ORDER BY n DESC LIMIT 20;

\echo '=== ir_model_data: count ของ account.move xmlid ใน __import15__ ==='
SELECT count(*) AS n
FROM ir_model_data d
WHERE d.module = '__import15__' AND d.model = 'account.move';

\echo '=== BRF moves: แต่ละใบมีบัญชีอะไร (สรุป AR/AP vs อื่น) ==='
SELECT m.name, m.date,
       count(*) AS lines,
       round(sum(CASE WHEN a.account_type IN ('asset_receivable','liability_payable') THEN l.balance ELSE 0 END)::numeric,2) AS arap,
       round(sum(l.balance)::numeric,2) AS total_bal
FROM account_move m
JOIN account_move_line l ON l.move_id = m.id
JOIN account_account a ON a.id = l.account_id
WHERE m.name LIKE 'BRF/2026/%'
GROUP BY m.name, m.date
ORDER BY m.name
LIMIT 10;

\echo '=== BRF moves ที่มี AR/AP (sample 10) ==='
SELECT m.name, m.date, a.account_type AS atype,
       (SELECT string_agg(value,'/') FROM jsonb_each_text(a.code_store)) AS code,
       round(sum(l.balance)::numeric,2) AS bal
FROM account_move m
JOIN account_move_line l ON l.move_id = m.id
JOIN account_account a ON a.id = l.account_id
WHERE m.name LIKE 'BRF/2026/%'
  AND a.account_type IN ('asset_receivable','liability_payable')
GROUP BY m.name, m.date, a.account_type, a.code_store
ORDER BY m.name
LIMIT 20;

\echo '=== BRF: ยอดรวม AR / AP ==='
SELECT a.account_type AS atype, round(sum(l.balance)::numeric,2) AS bal, count(*) AS lines
FROM account_move m
JOIN account_move_line l ON l.move_id = m.id
JOIN account_account a ON a.id = l.account_id
WHERE m.name LIKE 'BRF/2026/%'
  AND a.account_type IN ('asset_receivable','liability_payable')
GROUP BY a.account_type;

\echo '=== JV 2026 moves ทั้งหมด (ชื่อ/วันที่/ref) ==='
SELECT m.name, m.date, m.ref, m.state
FROM account_move m
WHERE m.name LIKE 'JV/2026/%'
ORDER BY m.date, m.name;

\echo '=== GL AR/AP ณ 2026-01-01 แยกตาม journal ==='
SELECT j.code AS journal, a.account_type AS atype, round(sum(l.balance)::numeric,2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_journal j ON j.id = m.journal_id
JOIN account_account a ON a.id = l.account_id
WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
  AND a.account_type IN ('asset_receivable','liability_payable')
GROUP BY j.code, a.account_type
ORDER BY a.account_type, j.code;

\echo '=== GL AR/AP ณ 2026-10-31 แยกตาม journal ==='
SELECT j.code AS journal, a.account_type AS atype, round(sum(l.balance)::numeric,2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_journal j ON j.id = m.journal_id
JOIN account_account a ON a.id = l.account_id
WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
  AND a.account_type IN ('asset_receivable','liability_payable')
GROUP BY j.code, a.account_type
ORDER BY a.account_type, j.code;
