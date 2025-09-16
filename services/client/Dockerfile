FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for simpleaudio
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "client.py"]
