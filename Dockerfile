FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY req.txt ./
RUN pip install --no-cache-dir -r req.txt

COPY app ./app

RUN mkdir -p /app/var/illustrations
VOLUME ["/app/var"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
