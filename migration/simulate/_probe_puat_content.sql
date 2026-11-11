\pset pager off

\echo '=== puat: external IDs ของ account_move ที่ tooling นำเข้า ==='
SELECT module, split_part(name, '.', 1) AS prefix, count(*) AS n
FROM ir_model_data WHERE model='account_move'
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 30;

\echo '=== puat: sample external IDs ของ account_move (__import15__) ==='
SELECT name, res_id FROM ir_model_data
WHERE model='account_move' AND module='__import15__'
ORDER BY name LIMIT 25;

\echo '=== puat: เนื้อใน JV/2026/0059-0062 ==='
SELECT m.name, m.date, m.ref, m.move_type, a.code, l.partner_id,
       round(l.debit,2) AS dr, round(l.credit,2) AS cr
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
WHERE m.name LIKE 'JV/2026/005%' OR m.name LIKE 'JV/2026/006%'
ORDER BY m.name, a.code, l.id;

\echo '=== puat: บัญชีใน BRF/2026/0125 (51 บรรทัด) ==='
SELECT a.code, a.account_type, round(sum(l.debit),2) AS dr, round(sum(l.credit),2) AS cr
FROM account_move_line l
JOIN account_move m ON m.id = l.move_id
JOIN account_account a ON a.id = l.account_id
WHERE m.name = 'BRF/2026/0125'
GROUP BY 1, 2 ORDER BY 1;

\echo '=== puat: create/uid ของใบสำคัญ (ดูว่ามาจาก import หรือ manual) ==='
SELECT name, date, move_type, create_date, write_date
FROM account_move
WHERE name IN ('BRF/2026/0001','BRF/2026/0124','BRF/2026/0125','JV/2026/0059','JV/2026/0062')
ORDER BY name;

\echo '=== puat: นับใบ 2026 ตาม move_type และปี ==='
SELECT to_char(m.date,'YYYY-MM') AS ym, m.move_type, count(*) AS n,
       round(sum(l.balance)::numeric,2) AS bal
FROM account_move m JOIN account_move_line l ON l.move_id=m.id
JOIN account_account a ON a.id=l.account_id
WHERE m.state='posted' AND a.account_type IN ('asset_receivable','liability_payable')
  AND m.date >= DATE '2026-01-01'
GROUP BY 1,2 ORDER BY 1,2;
