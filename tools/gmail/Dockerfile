FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    JOB_MODE=cloud

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auth.py scanner.py storage.py job_runner.py ./

CMD ["python", "job_runner.py"]
