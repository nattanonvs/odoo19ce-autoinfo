\pset pager off

\echo '=== odoo19_puat: account_move counts by move_type ==='
SELECT move_type, count(*) AS moves FROM account_move GROUP BY 1 ORDER BY 1;

\echo '=== odoo19_puat: imported xmlids (module=__import15__) for account.move ==='
SELECT count(*) AS xmlids,
       count(*) FILTER (WHERE name LIKE 'arap%') AS arap_like,
       count(*) FILTER (WHERE name LIKE 'opening_gl%') AS opening_gl_like
FROM ir_model_data WHERE module='__import15__' AND model='account.move';

\echo '=== odoo19_puat: BRF moves list ==='
SELECT m.id, m.name, m.move_type, m.state, m.date,
       imd.module || '.' || imd.name AS xmlid
FROM account_move m
LEFT JOIN ir_model_data imd ON imd.res_id=m.id AND imd.model='account.move'
WHERE m.name LIKE 'BRF/2026/%' ORDER BY m.name;

\echo '=== odoo19_puat: any existing invoice-type moves with names from od15 sample ==='
SELECT move_type, count(*) AS moves
FROM account_move
WHERE move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
GROUP BY 1;
