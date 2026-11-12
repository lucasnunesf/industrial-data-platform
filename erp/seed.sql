INSERT INTO work_centers (work_center_code, work_center_name, hourly_rate_brl) VALUES
    ('CUT',  'Laser Cutting',   180),
    ('WELD', 'Laser Welding',   150),
    ('FAB',  'Fabrication',      70),
    ('FIN',  'Finishing',        55),
    ('QC',   'Quality Control',  60)
ON CONFLICT (work_center_code) DO NOTHING;

INSERT INTO machines (machine_code, machine_name, work_center_id)
SELECT m.code, m.name, wc.work_center_id
FROM (VALUES
    ('LSR-01', 'Laser Cutter 01', 'CUT'),
    ('LSR-02', 'Laser Cutter 02', 'CUT'),
    ('WLD-01', 'Laser Welder 01', 'WELD')
) AS m(code, name, wc_code)
JOIN work_centers wc ON wc.work_center_code = m.wc_code
ON CONFLICT (machine_code) DO NOTHING;

INSERT INTO routings (routing_code, routing_name) VALUES
    ('CUT_ONLY', 'Laser cut only'),
    ('CUT_FAB',  'Cut, fabrication and finishing'),
    ('FULL',     'Cut, laser weld, fabrication and finishing')
ON CONFLICT (routing_code) DO NOTHING;

INSERT INTO routing_steps (routing_id, step_sequence, work_center_id)
SELECT r.routing_id, s.seq, wc.work_center_id
FROM (VALUES
    ('CUT_ONLY', 1, 'CUT'),
    ('CUT_FAB',  1, 'CUT'),
    ('CUT_FAB',  2, 'FAB'),
    ('CUT_FAB',  3, 'FIN'),
    ('FULL',     1, 'CUT'),
    ('FULL',     2, 'WELD'),
    ('FULL',     3, 'FAB'),
    ('FULL',     4, 'FIN')
) AS s(routing_code, seq, wc_code)
JOIN routings r      ON r.routing_code = s.routing_code
JOIN work_centers wc ON wc.work_center_code = s.wc_code
ON CONFLICT (routing_id, step_sequence) DO NOTHING;