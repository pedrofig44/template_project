# Use Python 3.11 as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apk update && \
    apk add --no-cache \
    postgresql-dev \
    gcc \
    g++ \
    cmake \
    make \
    python3-dev \
    musl-dev \
    geos \
    gdal-dev \
    rust \
    cargo \
    && rm -rf /var/cache/apk/*


# Set GDAL environment variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Run as non-root user
RUN useradd -m myuser
USER myuser