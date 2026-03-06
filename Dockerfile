FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY uniguru/requirements.txt /app/uniguru/requirements.txt
RUN pip install --no-cache-dir -r /app/uniguru/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "uniguru.service.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

