\pset pager off
\echo '=== partner receivable account distribution ==='
SELECT a.code, count(*) AS partners
FROM res_partner p
CROSS JOIN LATERAL jsonb_each_text(p.property_account_receivable_id) AS j
JOIN (SELECT id, (SELECT string_agg(value,'/') FROM jsonb_each_text(code_store)) AS code
      FROM account_account) a ON a.id = j.value::int
GROUP BY a.code ORDER BY 2 DESC;

\echo '=== partner payable account distribution ==='
SELECT a.code, count(*) AS partners
FROM res_partner p
CROSS JOIN LATERAL jsonb_each_text(p.property_account_payable_id) AS j
JOIN (SELECT id, (SELECT string_agg(value,'/') FROM jsonb_each_text(code_store)) AS code
      FROM account_account) a ON a.id = j.value::int
GROUP BY a.code ORDER BY 2 DESC;

\echo '=== partners with NO receivable property ==='
SELECT count(*) FROM res_partner p
WHERE p.property_account_receivable_id = '{}'::jsonb OR p.property_account_receivable_id IS NULL;
