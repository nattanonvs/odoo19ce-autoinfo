\pset pager off

\echo '=== puat: ALL invoice-type moves vs imported (__import15__) ==='
SELECT m.move_type, count(*) AS total,
       count(imd.id) AS imported,
       min(m.date) AS dmin, max(m.date) AS dmax,
       round(sum(m.amount_total_signed)::numeric,2) AS total_signed
FROM account_move m
LEFT JOIN ir_model_data imd ON imd.res_id=m.id AND imd.model='account.move'
     AND imd.module='__import15__'
WHERE m.move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
GROUP BY 1 ORDER BY 1;

\echo '=== puat: imported invoice-type moves by name prefix ==='
SELECT split_part(imd.name,'.',2) AS nm, m.move_type, count(*),
       round(sum(m.amount_total_signed)::numeric,2) AS total
FROM account_move m
JOIN ir_model_data imd ON imd.res_id=m.id AND imd.model='account.move'
WHERE imd.module='__import15__'
  AND m.move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
GROUP BY 1,2 ORDER BY 3 DESC LIMIT 30;

\echo '=== puat: imported out_invoice by year ==='
SELECT extract(year FROM m.date)::int AS yr, count(*),
       round(sum(m.amount_total_signed)::numeric,2) AS total
FROM account_move m
JOIN ir_model_data imd ON imd.res_id=m.id AND imd.model='account.move'
WHERE imd.module='__import15__' AND m.move_type='out_invoice'
GROUP BY 1 ORDER BY 1;

\echo '=== puat: ALL xmlid name-prefixes under __import15__ for account.move ==='
SELECT split_part(imd.name,'.',2) AS nm, count(*)
FROM ir_model_data imd
WHERE imd.module='__import15__' AND imd.model='account.move'
GROUP BY 1 ORDER BY 2 DESC LIMIT 25;
