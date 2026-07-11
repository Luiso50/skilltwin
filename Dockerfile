FROM python:3.12-slim

WORKDIR /app

COPY . /app

WORKDIR /app/cerebro

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "server.py"]
