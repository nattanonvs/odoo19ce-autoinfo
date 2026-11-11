\pset pager off

\echo '=== odoo19_puat: AR/AP balance per account (ALL posted moves, date<=2026-10-31) ==='
SELECT (SELECT string_agg(value,'/') FROM jsonb_each_text(a.code_store)) AS code,
       a.account_type, round(sum(l.balance)::numeric,2) AS balance
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
  AND a.account_type IN ('asset_receivable','liability_payable')
GROUP BY 1,2 ORDER BY 1;

\echo '=== odoo19_puat: AR/AP balance by move_type ==='
SELECT m.move_type,
       round(sum(l.balance)::numeric,2) AS balance, count(DISTINCT m.id) AS moves
FROM account_move_line l
JOIN account_move m ON m.id=l.move_id
JOIN account_account a ON a.id=l.account_id
WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
  AND a.account_type IN ('asset_receivable','liability_payable')
GROUP BY 1 ORDER BY 2;

\echo '=== odoo19_puat: out_invoice/in_invoice nonzero residual count & amount ==='
SELECT m.move_type, count(*) AS moves,
       round(sum(m.amount_total_signed)::numeric,2) AS total_signed,
       round(sum(m.amount_residual_signed)::numeric,2) AS residual_signed
FROM account_move m
WHERE m.state='posted' AND m.date <= DATE '2026-10-31'
  AND m.move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
GROUP BY 1 ORDER BY 1;
