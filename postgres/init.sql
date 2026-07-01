CREATE TABLE IF NOT EXISTS raw_customers (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    signup_date DATE,
    last_login_date DATE,
    monthly_spend NUMERIC(10, 2),
    support_tickets INT,
    plan_type VARCHAR(50),
    is_churned BOOLEAN,
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS features (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    days_since_signup INT,
    days_since_last_login INT,
    avg_monthly_spend NUMERIC(10, 2),
    support_ticket_count INT,
    is_premium BOOLEAN,
    is_churned BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    version_name VARCHAR(100) NOT NULL,
    accuracy NUMERIC(5, 4),
    precision_score NUMERIC(5, 4),
    recall_score NUMERIC(5, 4),
    file_path VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    trained_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50),
    prediction BOOLEAN,
    probability NUMERIC(5, 4),
    model_version_id INT REFERENCES model_versions(id),
    requested_by VARCHAR(100),
    predicted_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    dag_run_id VARCHAR(100),
    status VARCHAR(20),
    rows_processed INT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
