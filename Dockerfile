FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies (GDAL for GeoDjango)
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    postgresql-client \
    python3-dev \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]