-- Create synthetic employee data. Values are demo-only and not real PII.
-- principal_name and manager_principal_name intentionally match quoted lowercase
-- local end-user names such as "staff_tokyo".

CREATE TABLE {{DEMO_SCHEMA}}.employees (
  employee_id              NUMBER PRIMARY KEY,
  principal_name           VARCHAR2(64) NOT NULL,
  display_name             VARCHAR2(100) NOT NULL,
  job_title                VARCHAR2(100) NOT NULL,
  department               VARCHAR2(50) NOT NULL,
  country                  VARCHAR2(50) NOT NULL,
  city                     VARCHAR2(50) NOT NULL,
  manager_principal_name   VARCHAR2(64),
  employment_status        VARCHAR2(20) NOT NULL,
  salary_amount            NUMBER,
  personal_id              VARCHAR2(40),
  phone_number             VARCHAR2(40),
  CONSTRAINT employees_status_ck CHECK (employment_status IN ('ACTIVE', 'INACTIVE'))
);

COMMENT ON TABLE {{DEMO_SCHEMA}}.employees IS 'Synthetic employee data for the Oracle Deep Data Security direct-logon demo';
COMMENT ON COLUMN {{DEMO_SCHEMA}}.employees.personal_id IS 'Synthetic demo identifier, not real PII';
COMMENT ON COLUMN {{DEMO_SCHEMA}}.employees.phone_number IS 'Synthetic demo phone number, not a real phone number';

INSERT INTO {{DEMO_SCHEMA}}.employees VALUES
  (1001, 'staff_tokyo', '東京営業メンバー', 'Account Executive', 'Sales', 'Japan', 'Tokyo', 'manager_tokyo', 'ACTIVE', 7200000, 'SYN-PII-1001', '000-0100-1001');

INSERT INTO {{DEMO_SCHEMA}}.employees VALUES
  (1002, 'staff_yokohama', '横浜営業メンバー', 'Account Executive', 'Sales', 'Japan', 'Yokohama', 'manager_tokyo', 'ACTIVE', 6900000, 'SYN-PII-1002', '000-0100-1002');

INSERT INTO {{DEMO_SCHEMA}}.employees VALUES
  (1003, 'manager_tokyo', '東京営業マネージャ', 'Sales Manager', 'Sales', 'Japan', 'Tokyo', 'manager_japan', 'ACTIVE', 10500000, 'SYN-PII-1003', '000-0100-1003');

INSERT INTO {{DEMO_SCHEMA}}.employees VALUES
  (1004, 'staff_osaka', '大阪営業メンバー', 'Account Executive', 'Sales', 'Japan', 'Osaka', 'manager_japan', 'ACTIVE', 7100000, 'SYN-PII-1004', '000-0100-1004');

INSERT INTO {{DEMO_SCHEMA}}.employees VALUES
  (1005, 'manager_japan', '日本営業責任者', 'Country Sales Director', 'Sales', 'Japan', 'Tokyo', NULL, 'ACTIVE', 14500000, 'SYN-PII-1005', '000-0100-1005');

INSERT INTO {{DEMO_SCHEMA}}.employees VALUES
  (1006, 'staff_singapore', 'シンガポール営業メンバー', 'Account Executive', 'Sales', 'Singapore', 'Singapore', NULL, 'ACTIVE', 9000000, 'SYN-PII-1006', '000-0100-1006');

INSERT INTO {{DEMO_SCHEMA}}.employees VALUES
  (1007, 'ai_assistant', 'AIアシスタント', 'Application Principal', 'AI', 'N/A', 'N/A', NULL, 'ACTIVE', NULL, NULL, NULL);

CREATE INDEX {{DEMO_SCHEMA}}.emp_principal_ix ON {{DEMO_SCHEMA}}.employees(principal_name);
CREATE INDEX {{DEMO_SCHEMA}}.emp_manager_ix ON {{DEMO_SCHEMA}}.employees(manager_principal_name);
CREATE INDEX {{DEMO_SCHEMA}}.emp_scope_ix ON {{DEMO_SCHEMA}}.employees(country, department, employment_status);

COMMIT;
