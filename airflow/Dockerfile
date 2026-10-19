# Airflow plus a separate virtualenv (/opt/pipeline) for our pipeline code.
# Airflow pins hundreds of its own packages; keeping dbt, scikit-learn and the app's
# packages in their own env means they can never conflict with Airflow's.
# It installs the same requirements.txt as the app image, so a model trained here
# is loaded by the exact same scikit-learn/pandas versions that serve predictions.
FROM apache/airflow:3.3.2-python3.13

USER root
RUN python -m venv /opt/pipeline && chown -R airflow:0 /opt/pipeline
USER airflow

COPY requirements.txt requirements-pipeline.txt /tmp/
RUN /opt/pipeline/bin/pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-pipeline.txt

# Download DuckDB's S3 extensions now, so pipeline runs don't depend on fetching them
RUN /opt/pipeline/bin/python -c "import duckdb; c = duckdb.connect(); c.install_extension('httpfs'); c.install_extension('aws')"
