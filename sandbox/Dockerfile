FROM python:3.12-slim
COPY probe_worker.py /worker.py
USER 65534:65534
ENTRYPOINT ["python", "-I", "-B", "/worker.py"]
