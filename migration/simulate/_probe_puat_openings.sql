\pset pager off

\echo '=== puat: BRF / JV moves (<=2026-10-31) — ใบและยอดรวม ==='
SELECT m.id, m.name, m.date, j.code AS journal, m.move_type, m.state,
       count(l.id) AS lines, round(sum(l.balance)::numeric,2) AS bal
FROM account_move m
JOIN account_journal j ON j.id=m.journal_id
LEFT JOIN account_move_line l ON l.move_id=m.id
WHERE m.date <= DATE '2026-10-31' AND j.code IN ('BRF','JV') AND m.state='posted'
GROUP BY m.id, m.name, m.date, j.code, m.move_type, m.state
ORDER BY m.date, j.code, m.name;

\echo '=== puat: BRF moves — แยกตามวันที่ (จำนวนใบ/บรรทัด/ยอด) ==='
SELECT m.date, m.name, count(l.id) AS lines, round(sum(l.balance)::numeric,2) AS bal
FROM account_move m
JOIN account_journal j ON j.id=m.journal_id
LEFT JOIN account_move_line l ON l.move_id=m.id
WHERE j.code='BRF' AND m.state='posted'
GROUP BY m.date, m.name ORDER BY m.date, m.name;

\echo '=== puat: JV moves ในปี 2026 — จำนวนใบ/บรรทัด/ยอด ==='
SELECT m.date, m.name, count(l.id) AS lines, round(sum(l.balance)::numeric,2) AS bal
FROM account_move m
JOIN account_journal j ON j.id=m.journal_id
LEFT JOIN account_move_line l ON l.move_id=m.id
WHERE j.code='JV' AND m.date >= DATE '2026-01-01' AND m.state='posted'
GROUP BY m.date, m.name ORDER BY m.date, m.name;

\echo '=== puat: เนื้อใน JV/2026/0062 (ทุกบรรทัด) ==='
SELECT a.code, a.name->>'en_US' AS accname, l.partner_id, l.name AS label,
       round(l.debit,2) AS debit, round(l.credit,2) AS credit, round(l.balance,2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
WHERE m.name='JV/2026/0062'
ORDER BY a.code, l.id;

\echo '=== puat: AR/AP balance by journal (ยืนยันยอดซ้ำ) ==='
SELECT aa.account_type, j.code, round(sum(l.balance)::numeric,2) AS bal, count(*) AS lines
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id
JOIN account_journal j ON j.id=m.journal_id
WHERE m.state='posted' AND aa.account_type IN ('asset_receivable','liability_payable')
GROUP BY 1,2 ORDER BY 1,2;

\echo '=== puat: BRF moves ที่มีเฉพาะ AR/AP (กี่ใบ) ==='
SELECT m.name, count(l.id) AS lines, round(sum(l.balance)::numeric,2) AS bal
FROM account_move m
JOIN account_journal j ON j.id=m.journal_id
JOIN account_move_line l ON l.move_id=m.id
JOIN account_account aa ON aa.id=l.account_id
WHERE j.code='BRF' AND m.state='posted'
  AND aa.account_type IN ('asset_receivable','liability_payable')
GROUP BY m.name ORDER BY m.name;
