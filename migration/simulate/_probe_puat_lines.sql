\pset pager off

\echo '=== puat: เนื้อใน JV/2026/0059-0062 (66 บรรทัด) ==='
SELECT m.name, m.date, m.ref,
       (SELECT string_agg(value, '/') FROM jsonb_each_text(a.code_store)) AS code,
       a.account_type AS atype, l.partner_id,
       round(l.debit,2) AS dr, round(l.credit,2) AS cr
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
WHERE (m.name LIKE 'JV/2026/005%' OR m.name LIKE 'JV/2026/006%')
  AND m.date = DATE '2026-01-01'
ORDER BY m.name, code, l.id;

\echo '=== puat: บัญชีใน BRF/2026/0125 (51 บรรทัด) ==='
SELECT (SELECT string_agg(value, '/') FROM jsonb_each_text(a.code_store)) AS code,
       a.account_type AS atype, round(sum(l.debit),2) AS dr, round(sum(l.credit),2) AS cr
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
WHERE m.name = 'BRF/2026/0125'
GROUP BY 1, 2 ORDER BY 1;

\echo '=== puat: GL trial balance ณ 2026-01-01 (ก่อน/หลังใส่ opening) ==='
SELECT (SELECT string_agg(value, '/') FROM jsonb_each_text(a.code_store)) AS code,
       a.account_type AS atype, round(sum(l.balance)::numeric,2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
WHERE m.state='posted' AND m.date <= DATE '2026-01-01'
GROUP BY 1,2 HAVING round(sum(l.balance)::numeric,2) <> 0
ORDER BY 1;

\echo '=== puat: อายุข้อมูล 2026 activity (min/max date ต่อ move_type) ==='
SELECT m.move_type, min(m.date) AS d1, max(m.date) AS d2, count(*) AS n
FROM account_move m WHERE m.state='posted'
GROUP BY 1 ORDER BY 1;
