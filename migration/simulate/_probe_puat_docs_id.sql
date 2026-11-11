\pset pager off

\echo '=== puat: out_invoice sample (name, date, partner, xmlid) ==='
SELECT m.id, m.name, m.date, m.state, m.partner_id, m.amount_total_signed,
       CASE WHEN imd.id IS NULL THEN '(no xmlid)' ELSE imd.module||'.'||imd.name END AS xmlid
FROM account_move m
LEFT JOIN ir_model_data imd ON imd.res_id=m.id AND imd.model='account.move'
WHERE m.move_type='out_invoice'
ORDER BY m.id LIMIT 15;

\echo '=== puat: out_invoice how many have __import15__ xmlid? ==='
SELECT count(*) AS total,
       count(imd.id) AS with_any_xmlid,
       count(*) FILTER (WHERE imd.module='__import15__') AS with_import15
FROM account_move m
LEFT JOIN ir_model_data imd ON imd.res_id=m.id AND imd.model='account.move'
WHERE m.move_type='out_invoice';

\echo '=== puat: in_invoice sample ==='
SELECT m.id, m.name, m.date, m.partner_id, m.amount_total_signed,
       CASE WHEN imd.id IS NULL THEN '(no xmlid)' ELSE imd.module||'.'||imd.name END AS xmlid
FROM account_move m
LEFT JOIN ir_model_data imd ON imd.res_id=m.id AND imd.model='account_move'
WHERE m.move_type='in_invoice'
ORDER BY m.id LIMIT 15;

\echo '=== puat: names matching od15 real-doc pattern (IV..., IS...) ==='
SELECT m.move_type, count(*) FROM account_move m
WHERE m.move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
  AND (m.name LIKE 'IV%' OR m.name LIKE 'IS%' OR m.name LIKE 'BILL%' OR m.name LIKE 'INV/%')
GROUP BY 1;
