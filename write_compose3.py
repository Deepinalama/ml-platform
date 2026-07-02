content = open('docker-compose.yml').read()
content = """services:
  postgres:
    image: postgres:15
    container_name: ml_platform_postgres
    restart: always
    env_file:
      - .env
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./postgres/00_create_airflow_db.sql:/docker-entrypoint-initdb.d/00_create_airflow_db.sql
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/10_init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - ml_platform_net

  airflow-init:
    build: ./airflow
    container_name: ml_platform_airflow_init
    depends_on:
      postgres:
        condition: service_healthy
    env_file:
      - .env
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${AIRFLOW_DB}
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
      AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW_SECRET_KEY}
      AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./shared/model_storage:/opt/airflow/model_storage
    entrypoint: /bin/bash
    command:
      - -c
      - |
        airflow db migrate
        airflow users create --username ${AIRFLOW_ADMIN_USER} --password ${AIRFLOW_ADMIN_PASSWORD} --firstname Admin --lastname User --role Admin --email admin@example.com || true
    networks:
      - ml_platform_net

  airflow-webserver:
    build: ./airflow
    container_name: ml_platform_airflow_webserver
    restart: always
    depends_on:
      - airflow-init
    env_file:
      - .env
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${AIRFLOW_DB}
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
      AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW_SECRET_KEY}
      AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    ports:
      - "8080:8080"
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./shared/model_storage:/opt/airflow/model_storage
    command: webserver
    networks:
      - ml_platform_net

  airflow-scheduler:
    build: ./airflow
    container_name: ml_platform_airflow_scheduler
    restart: always
    depends_on:
      - airflow-init
    env_file:
      - .env
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${AIRFLOW_DB}
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
      AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW_SECRET_KEY}
      AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./shared/model_storage:/opt/airflow/model_storage
    command: scheduler
    networks:
      - ml_platform_net

  fastapi:
    build: ./fastapi_app
    container_name: ml_platform_fastapi
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DB_USER: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: ${POSTGRES_DB}
    ports:
      - "8000:8000"
    volumes:
      - ./shared/model_storage:/opt/airflow/model_storage
    networks:
      - ml_platform_net

  django:
    build: ./django_app
    container_name: ml_platform_django
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DB_USER: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: ${POSTGRES_DB}
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY}
      AIRFLOW_API_URL: http://airflow-webserver:8080/api/v1
      AIRFLOW_ADMIN_USER: ${AIRFLOW_ADMIN_USER}
      AIRFLOW_ADMIN_PASSWORD: ${AIRFLOW_ADMIN_PASSWORD}
    ports:
      - "8001:8001"
    networks:
      - ml_platform_net

volumes:
  pgdata:

networks:
  ml_platform_net:
    driver: bridge
"""

with open('docker-compose.yml', 'w') as f:
    f.write(content)
print('Done - docker-compose.yml updated with Django service')