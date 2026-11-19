\pset pager off

-- แยกยอด AR/AP ใน puat ตาม "แหล่งที่มา" (xmlid) ณ 2026-10-31
-- ใช้ eval residual แบบเดียวกับ probe อื่น (debit-credit + partial หลังวันเป้าหมาย)
CREATE TEMP VIEW ar_ap AS
SELECT * FROM (
  SELECT m.id AS move_id, m.move_type, m.name AS move_name,
         a.account_type,
         CASE WHEN imd.id IS NULL THEN '(no-xmlid)'
              WHEN imd.name LIKE 'account_move.gl15rep\_%' THEN 'gl15rep (replicate)'
              WHEN imd.name LIKE 'account_move.arap\_%'     THEN 'arap (BRF opening)'
              WHEN imd.name LIKE 'account_move.opening\_%'  THEN 'opening_gl'
              ELSE COALESCE(imd.module, '?') || '.' || COALESCE(imd.name, '(none)')
         END AS src,
         l.partner_id,
         l.debit - l.credit
           + COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id = p.debit_move_id
                       JOIN account_move cm ON cm.id = cl.move_id
                       WHERE p.credit_move_id = l.id AND cm.date <= DATE '2026-10-31'), 0)
           - COALESCE((SELECT sum(p.amount) FROM account_partial_reconcile p
                       JOIN account_move_line cl ON cl.id = p.credit_move_id
                       JOIN account_move cm ON cm.id = cl.move_id
                       WHERE p.debit_move_id = l.id AND cm.date <= DATE '2026-10-31'), 0)
           AS resid
  FROM account_move_line l
  JOIN account_move m ON m.id = l.move_id
  JOIN account_account a ON a.id = l.account_id
  LEFT JOIN ir_model_data imd ON imd.res_id = m.id AND imd.model = 'account.move'
  WHERE m.state = 'posted' AND m.date <= DATE '2026-10-31'
    AND a.account_type IN ('asset_receivable', 'liability_payable')
) s;

\echo '=== AR/AP residual by (account_type, source) ==='
SELECT account_type, src,
       count(DISTINCT move_id) AS moves,
       round(sum(resid)::numeric, 2) AS resid
FROM ar_ap
WHERE round(resid::numeric, 2) <> 0
GROUP BY 1, 2
ORDER BY 1, 4 DESC;

\echo '=== TOTAL by account_type ==='
SELECT account_type,
       count(DISTINCT move_id) AS moves,
       round(sum(resid)::numeric, 2) AS resid
FROM ar_ap
WHERE round(resid::numeric, 2) <> 0
GROUP BY 1 ORDER BY 1;

\echo '=== gl15rep only: by move_type ==='
SELECT move_type,
       count(DISTINCT move_id) AS moves,
       round(sum(resid)::numeric, 2) AS resid
FROM ar_ap
WHERE src = 'gl15rep (replicate)' AND round(resid::numeric, 2) <> 0
GROUP BY 1 ORDER BY 1;
