from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import random
import pickle
import os
from faker import Faker
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score

fake = Faker()

MODEL_STORAGE_PATH = "/opt/airflow/model_storage"
CONN_ID = "ml_platform_postgres"

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

# ─────────────────────────────────────────
# TASK 1: Generate and insert raw customers
# ─────────────────────────────────────────
def fetch_data():
    hook = PostgresHook(postgres_conn_id=CONN_ID)
    conn = hook.get_conn()
    cursor = conn.cursor()

    rows = []
    for _ in range(200):
        support_tickets = random.randint(0, 10)
        days_since_login = random.randint(1, 120)
        monthly_spend = round(random.uniform(10, 500), 2)
        plan_type = random.choice(["basic", "standard", "premium"])

        # Churn logic: high tickets + low spend + long since login = likely churn
        churn_score = (
            (support_tickets / 10) * 0.4 +
            (days_since_login / 120) * 0.4 +
            ((500 - monthly_spend) / 500) * 0.2
        )
        is_churned = churn_score > 0.5 if random.random() > 0.1 else not (churn_score > 0.5)

        rows.append((
            fake.uuid4(),
            fake.date_between(start_date="-2y", end_date="-30d"),
            fake.date_between(start_date=f"-{days_since_login}d", end_date="today"),
            monthly_spend,
            support_tickets,
            plan_type,
            is_churned,
        ))

    cursor.executemany("""
        INSERT INTO raw_customers
            (customer_id, signup_date, last_login_date, monthly_spend,
             support_tickets, plan_type, is_churned)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, rows)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Inserted {len(rows)} raw customer rows")


# ─────────────────────────────────────────
# TASK 2: Transform raw data into features
# ─────────────────────────────────────────
def transform_features():
    hook = PostgresHook(postgres_conn_id=CONN_ID)
    conn = hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            customer_id,
            (CURRENT_DATE - signup_date) AS days_since_signup,
            (CURRENT_DATE - last_login_date) AS days_since_last_login,
            monthly_spend,
            support_tickets,
            plan_type,
            is_churned
        FROM raw_customers
        WHERE customer_id NOT IN (SELECT customer_id FROM features)
    """)

    rows = cursor.fetchall()
    if not rows:
        print("No new rows to transform")
        cursor.close()
        conn.close()
        return

    feature_rows = []
    for row in rows:
        customer_id, days_signup, days_login, spend, tickets, plan, churned = row
        is_premium = plan == "premium"
        feature_rows.append((
            customer_id,
            int(days_signup),
            int(days_login),
            float(spend),
            int(tickets),
            is_premium,
            churned,
        ))

    cursor.executemany("""
        INSERT INTO features
            (customer_id, days_since_signup, days_since_last_login,
             avg_monthly_spend, support_ticket_count, is_premium, is_churned)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, feature_rows)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Transformed {len(feature_rows)} rows into features")


# ─────────────────────────────────────────
# TASK 3: Train the ML model
# ─────────────────────────────────────────
def train_model(**context):
    hook = PostgresHook(postgres_conn_id=CONN_ID)
    conn = hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT days_since_signup, days_since_last_login,
               avg_monthly_spend, support_ticket_count,
               is_premium::int, is_churned::int
        FROM features
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if len(rows) < 50:
        print(f"Not enough data to train ({len(rows)} rows). Need at least 50.")
        return

    df = pd.DataFrame(rows, columns=[
        "days_since_signup", "days_since_last_login",
        "avg_monthly_spend", "support_ticket_count",
        "is_premium", "is_churned"
    ])

    X = df.drop("is_churned", axis=1)
    y = df["is_churned"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = round(accuracy_score(y_test, y_pred), 4)
    prec = round(precision_score(y_test, y_pred, zero_division=0), 4)
    rec = round(recall_score(y_test, y_pred, zero_division=0), 4)

    print(f"Model trained — Accuracy: {acc}, Precision: {prec}, Recall: {rec}")

    # Save model to shared volume
    os.makedirs(MODEL_STORAGE_PATH, exist_ok=True)
    run_id = context["run_id"].replace(":", "_").replace("+", "_")
    model_filename = f"churn_model_{run_id}.pkl"
    model_path = os.path.join(MODEL_STORAGE_PATH, model_filename)

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"Model saved to {model_path}")

    # Push metrics to XCom so next task can use them
    context["ti"].xcom_push(key="accuracy", value=acc)
    context["ti"].xcom_push(key="precision", value=prec)
    context["ti"].xcom_push(key="recall", value=rec)
    context["ti"].xcom_push(key="model_path", value=model_path)
    context["ti"].xcom_push(key="version_name", value=model_filename)


# ─────────────────────────────────────────
# TASK 4: Register model in model_versions
# ─────────────────────────────────────────
def register_model(**context):
    ti = context["ti"]
    accuracy = ti.xcom_pull(key="accuracy", task_ids="train_model")
    precision = ti.xcom_pull(key="precision", task_ids="train_model")
    recall = ti.xcom_pull(key="recall", task_ids="train_model")
    model_path = ti.xcom_pull(key="model_path", task_ids="train_model")
    version_name = ti.xcom_pull(key="version_name", task_ids="train_model")

    if not model_path:
        print("No model was trained, skipping registration")
        return

    hook = PostgresHook(postgres_conn_id=CONN_ID)
    conn = hook.get_conn()
    cursor = conn.cursor()

    # Deactivate all previous models
    cursor.execute("UPDATE model_versions SET is_active = FALSE")

    # Register new model as active
    cursor.execute("""
        INSERT INTO model_versions
            (version_name, accuracy, precision_score, recall_score, file_path, is_active)
        VALUES (%s, %s, %s, %s, %s, TRUE)
    """, (version_name, accuracy, precision, recall, model_path))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Registered model {version_name} with accuracy {accuracy}")


# ─────────────────────────────────────────
# DAG definition
# ─────────────────────────────────────────
with DAG(
    dag_id="churn_prediction_pipeline",
    default_args=default_args,
    description="End-to-end churn prediction pipeline",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ml", "churn", "pipeline"],
) as dag:

    t1 = PythonOperator(
        task_id="fetch_data",
        python_callable=fetch_data,
    )

    t2 = PythonOperator(
        task_id="transform_features",
        python_callable=transform_features,
    )

    t3 = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
        provide_context=True,
    )

    t4 = PythonOperator(
        task_id="register_model",
        python_callable=register_model,
        provide_context=True,
    )

    t1 >> t2 >> t3 >> t4