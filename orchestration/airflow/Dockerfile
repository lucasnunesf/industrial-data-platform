# Airflow image with the pipeline tools installed in their own virtual environments,
# so their dependencies never clash with Airflow's.
# Build context: repository root (see docker-compose.yml).
FROM apache/airflow:3.1.0

USER root

# Microsoft ODBC Driver 18: dbt-fabric needs it to reach the Fabric Warehouse.
# ACCEPT_EULA=Y accepts the Microsoft driver license.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# /opt/venvs holds the tools; /opt/airflow/azure keeps the Azure CLI logins (a Docker volume).
RUN mkdir -p /opt/venvs /opt/airflow/azure/lake /opt/airflow/azure/fabric \
    && chown -R airflow /opt/venvs /opt/airflow/azure

USER airflow
ENV PIP_USER=false

# 1. simulator + extraction + upload
COPY simulator/requirements.txt /tmp/req/simulator.txt
COPY ingestion/requirements.txt /tmp/req/ingestion.txt
COPY ingestion/requirements-upload.txt /tmp/req/upload.txt
RUN python -m venv /opt/venvs/pipeline \
    && /opt/venvs/pipeline/bin/pip install --no-cache-dir \
       -r /tmp/req/simulator.txt -r /tmp/req/ingestion.txt -r /tmp/req/upload.txt

# 2. dbt
RUN python -m venv /opt/venvs/dbt \
    && /opt/venvs/dbt/bin/pip install --no-cache-dir dbt-fabric

# 3. Azure CLI: upload.py and dbt (authentication: CLI) both take their token from `az`
RUN python -m venv /opt/venvs/az \
    && /opt/venvs/az/bin/pip install --no-cache-dir azure-cli

ENV PATH="/opt/venvs/az/bin:${PATH}"
