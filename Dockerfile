# ============================================
# ADX-Auto Dockerfile for Render Deployment
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend
COPY app-source.tar.gz /build/
RUN cd /build && tar xzf app-source.tar.gz

WORKDIR /build/frontend
RUN npm install --no-audit --no-fund --loglevel=error
RUN npm run build

# ============================================
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and extract source code
COPY app-source.tar.gz /tmp/
RUN cd /tmp && tar xzf app-source.tar.gz && \
    cp -r /tmp/backend/* /app/ && \
    rm -rf /tmp/app-source.tar.gz

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend build to Flask static directory
RUN mkdir -p app/static
COPY --from=frontend-builder /build/frontend/dist/* app/static/

# Environment variables
ENV FLASK_ENV=production
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "run:app"]
