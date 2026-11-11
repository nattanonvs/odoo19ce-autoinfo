-- ตรวจรายชื่อใบ BRF/2026/xxxx ใน odoo19_puat พร้อม external id และยอด
SELECT m.name AS move_name,
       imd.module || '.' || imd.name AS xmlid,
       m.state,
       m.move_type,
       m.date,
       round(sum(l.debit - l.credit)::numeric, 2) AS amount
FROM account_move m
JOIN account_move_line l ON l.move_id = m.id
LEFT JOIN ir_model_data imd ON imd.res_id = m.id AND imd.model = 'account.move'
WHERE m.name LIKE 'BRF/2026/%'
GROUP BY m.name, imd.module, imd.name, m.state, m.move_type, m.date
ORDER BY m.name;
