# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8900

# Install LibreOffice (headless) for conversion
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8900

# In container, soffice is in PATH
ENV LIBREOFFICE_PATH=soffice

CMD ["python", "main.py"]

# docker-compose up --force-recreate --build -d
# docker save -o convert-to-pdf.tar convert-to-pdf:latest