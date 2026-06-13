-- =============================================================================
-- Minerva Lab — synthetic citizen + portal-user seed data (no real PII, §7)
-- Names, IDs, emails, and hashes are all fabricated for the isolated lab.
-- =============================================================================

INSERT INTO citizens (full_name, dob, county, benefit_program, status, state_id, email) VALUES
('Dana R. Holloway',     '1984-03-11', 'Monroe',     'SNAP',          'active',   'NY-ST-44120', 'dholloway@example.lab'),
('Marcus T. Bell',       '1979-09-02', 'Erie',       'Medicaid',      'review',   'NY-ST-44121', 'mbell@example.lab'),
('Priya N. Anand',       '1991-12-19', 'Onondaga',   'TANF',          'active',   'NY-ST-44122', 'panand@example.lab'),
('Gregory Olsen',        '1968-06-30', 'Monroe',     'SNAP',          'active',   'NY-ST-44123', 'golsen@example.lab'),
('Latoya Simmons',       '1995-01-25', 'Albany',     'Medicaid',      'active',   'NY-ST-44124', 'lsimmons@example.lab'),
('Hiroshi Tanaka',       '1972-11-08', 'Westchester','Unemployment',  'closed',   'NY-ST-44125', 'htanaka@example.lab'),
('Amara Okafor',         '1988-07-14', 'Erie',       'SNAP',          'active',   'NY-ST-44126', 'aokafor@example.lab'),
('Diego Marquez',        '1990-04-03', 'Bronx',      'TANF',          'review',   'NY-ST-44127', 'dmarquez@example.lab'),
('Caitlin O''Rourke',    '1983-02-17', 'Monroe',     'Medicaid',      'active',   'NY-ST-44128', 'corourke@example.lab'),
('Samuel Greenfield',    '1965-10-21', 'Suffolk',    'SNAP',          'active',   'NY-ST-44129', 'sgreenfield@example.lab'),
('Mei-Ling Chen',        '1997-08-09', 'Queens',     'Unemployment',  'active',   'NY-ST-44130', 'mchen@example.lab'),
('Robert Vance',         '1974-05-12', 'Onondaga',   'Medicaid',      'review',   'NY-ST-44131', 'rvance@example.lab'),
('Fatima Al-Sayed',      '1986-03-28', 'Albany',     'TANF',          'active',   'NY-ST-44132', 'falsayed@example.lab'),
('Jonathan Pierce',      '1992-09-16', 'Erie',       'SNAP',          'closed',   'NY-ST-44133', 'jpierce@example.lab'),
('Nadia Petrova',        '1981-12-01', 'Monroe',     'Medicaid',      'active',   'NY-ST-44134', 'npetrova@example.lab'),
('Terrence Booker',      '1970-07-23', 'Bronx',      'Unemployment',  'review',   'NY-ST-44135', 'tbooker@example.lab'),
('Isabella Romano',      '1999-02-14', 'Westchester','TANF',          'active',   'NY-ST-44136', 'iromano@example.lab'),
('Kwame Mensah',         '1985-11-05', 'Suffolk',    'SNAP',          'active',   'NY-ST-44137', 'kmensah@example.lab'),
('Helen Whitaker',       '1962-04-19', 'Onondaga',   'Medicaid',      'active',   'NY-ST-44138', 'hwhitaker@example.lab'),
('Victor Nguyen',        '1993-06-27', 'Queens',     'Unemployment',  'closed',   'NY-ST-44139', 'vnguyen@example.lab'),
('Rosa Delgado',         '1989-10-30', 'Albany',     'SNAP',          'active',   'NY-ST-44140', 'rdelgado@example.lab'),
('Patrick Donnelly',     '1977-01-08', 'Monroe',     'Medicaid',      'review',   'NY-ST-44141', 'pdonnelly@example.lab'),
('Aaliyah Jefferson',    '1996-03-22', 'Erie',       'TANF',          'active',   'NY-ST-44142', 'ajefferson@example.lab'),
('Sven Eriksson',        '1971-08-13', 'Westchester','SNAP',          'active',   'NY-ST-44143', 'seriksson@example.lab');

-- Portal users. Passwords are unsalted MD5 of obvious strings — the kind of
-- secondary loot a UNION-based SQLi would surface. Synthetic accounts only.
--   admin   -> md5('admin123')         = 0192023a7bbd73250516f069df18b500
--   svc_rag -> md5('rag-service-2026')  = 8d3e... (illustrative seed value)
--   clerk1  -> md5('password1')         = 7c6a180b36896a0a8c02787eeafb0e4c
INSERT INTO portal_users (username, password_md5, role, federal_scope) VALUES
('admin',   '0192023a7bbd73250516f069df18b500', 'administrator', TRUE),
('svc_rag', '5f4dcc3b5aa765d61d8327deb882cf99', 'service',       FALSE),
('clerk1',  '7c6a180b36896a0a8c02787eeafb0e4c', 'clerk',         FALSE),
('clerk2',  '6cb75f652a9b52798eb6cf2201057c73', 'clerk',         FALSE),
('auditor', 'e10adc3949ba59abbe56e057f20f883e', 'auditor',       TRUE);
