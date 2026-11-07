FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONPATH=/app/student:/app/webapp PYTHONDONTWRITEBYTECODE=1
COPY student/requirements-runtime.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY student/inference.py student/vocabulary.json student/model_original.onnx student/model_deployed.onnx /app/student/
COPY webapp/app.py webapp/auth.py webapp/index.html /app/webapp/
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "app:from_env", "--factory", "--host", "0.0.0.0", "--port", "8080"]
