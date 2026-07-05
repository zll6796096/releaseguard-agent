FROM python:3.12-slim

# Create a non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

WORKDIR /app

# Copy requirements first to leverage caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and set owner
COPY --chown=appuser:appgroup . .

# Run under the non-root user context
USER appuser

EXPOSE 8080

# Bind to 0.0.0.0 and dynamic port assigned by Cloud Run (default to 8080)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
