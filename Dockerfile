# Use Python slim image to reduce size
FROM python:3.11-slim

# Set environment variables to disable caching
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy project configuration first
COPY pyproject.toml ./

# Copy Python source files
COPY *.py ./

# Copy Flask app directories
COPY templates/ templates/
COPY static/ static/

# Install the package in editable mode without cache
RUN pip install --no-cache-dir --no-deps -e .

# Install dependencies separately 
RUN pip install --no-cache-dir flask flask-sqlalchemy gunicorn psycopg2-binary spacy sqlalchemy werkzeug

# Create necessary directories
RUN mkdir -p uploads results instance

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "main:app"]