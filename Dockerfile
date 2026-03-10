FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY uniguru/requirements.txt /app/uniguru/requirements.txt
RUN pip install --no-cache-dir -r /app/uniguru/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn uniguru.service.api:app --host ${UNIGURU_HOST:-0.0.0.0} --port ${UNIGURU_PORT:-8000} --workers ${UNIGURU_WORKERS:-4}"]
