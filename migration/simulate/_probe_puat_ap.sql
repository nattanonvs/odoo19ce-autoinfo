\pset pager off
\echo '=== puat: AP balance by journal ==='
SELECT j.code, j.name->>'en_US' AS jname, m.move_type, round(sum(l.balance),2) AS bal, count(*) AS lines
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_journal j ON j.id=m.journal_id
JOIN account_account aa ON aa.id=l.account_id
WHERE m.state='posted' AND aa.account_type='liability_payable'
GROUP BY 1,2,3 ORDER BY round(sum(l.balance),2) ASC;

\echo '=== puat: AP balance by year ==='
SELECT to_char(m.date,'YYYY') AS yr, round(sum(l.balance),2) AS bal, count(*) AS lines
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id
WHERE m.state='posted' AND aa.account_type='liability_payable'
GROUP BY 1 ORDER BY 1;

\echo '=== puat: AP lines named ยอดยกมา (top) ==='
SELECT m.name, m.date, round(sum(l.balance),2) AS bal, count(*) AS lines
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id
WHERE aa.account_type='liability_payable' AND l.name='ยอดยกมา'
GROUP BY 1,2 ORDER BY 2 LIMIT 10;

\echo '=== puat: AP ยอดยกมา grand total ==='
SELECT round(sum(l.balance),2) AS bal, count(*) AS lines
FROM account_move_line l JOIN account_move m ON m.id=l.move_id
JOIN account_account aa ON aa.id=l.account_id
WHERE aa.account_type='liability_payable' AND l.name='ยอดยกมา';
