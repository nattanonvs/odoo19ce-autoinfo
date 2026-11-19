\pset pager off
\echo '=== AR/AP/equity accounts by code ==='
SELECT a.id,
       (SELECT string_agg(value,'/') FROM jsonb_each_text(a.code_store)) AS code,
       a.name->>'en_US' AS name,
       a.account_type
FROM account_account a
WHERE (SELECT string_agg(value,'/') FROM jsonb_each_text(a.code_store))
      IN ('1130.01','1130.03','2131.01','2131.02','2132.02','2213.06','2213.08','999999')
   OR a.account_type IN ('equity_unaffected')
ORDER BY 2;

\echo '=== partner receivable account distribution ==='
SELECT a.code, count(*) AS partners
FROM res_partner p
CROSS JOIN LATERAL jsonb_each_text(p.property_account_receivable_id) AS j(k, v)
JOIN (SELECT id, (SELECT string_agg(value,'/') FROM jsonb_each_text(code_store)) AS code
      FROM account_account) a ON a.id = j.value::int
WHERE j.value <> ''
GROUP BY a.code ORDER BY 2 DESC;

\echo '=== partner payable account distribution ==='
SELECT a.code, count(*) AS partners
FROM res_partner p
CROSS JOIN LATERAL jsonb_each_text(p.property_account_payable_id) AS j(k, v)
JOIN (SELECT id, (SELECT string_agg(value,'/') FROM jsonb_each_text(code_store)) AS code
      FROM account_account) a ON a.id = j.value::int
WHERE j.value <> ''
GROUP BY a.code ORDER BY 2 DESC;

\echo '=== current AR/AP balance in puat by account ==='
SELECT a.code, t.type, round(sum(l.debit-l.credit)::numeric,2) AS bal
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN (SELECT id, (SELECT string_agg(value,'/') FROM jsonb_each_text(code_store)) AS code FROM account_account) a ON a.id=l.account_id
JOIN account_account aa ON aa.id=l.account_id
JOIN (SELECT DISTINCT account_type AS type FROM account_account) t ON t.type=aa.account_type
WHERE m.state='posted' AND aa.account_type IN ('asset_receivable','liability_payable')
  AND m.name LIKE 'BRF/2026/%'
GROUP BY a.code, t.type ORDER BY 2,1;
