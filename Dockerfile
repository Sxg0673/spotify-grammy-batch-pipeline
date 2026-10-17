FROM apache/airflow:3.1.8

COPY requirements.txt /requirements.txt

# Se reinstala apache-airflow en la misma versión para que pip no cambie la de la imagen
RUN pip install --no-cache-dir "apache-airflow==3.1.8" -r /requirements.txt
