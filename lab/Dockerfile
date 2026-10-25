FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libseccomp2 && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir Flask==3.1.2 gunicorn==23.0.0 && useradd -u 10002 -m worker
WORKDIR /worker
COPY lab/worker.py lab/child.py ./
USER worker
CMD ["gunicorn", "--bind", "0.0.0.0:7000", "--workers", "1", "--threads", "2", "--timeout", "10", "worker:app"]
