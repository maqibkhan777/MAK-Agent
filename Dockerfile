# Base Image: Official lightweight Python 3.11 slim image
FROM python:3.11-slim

# Configure environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    PHOENIX_PORT=6060 \
    PHOENIX_HOST=0.0.0.0

# Set working directory inside the container
WORKDIR /app

# Install system dependencies required for compilation, SQLite, and network utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements manifest and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser dependencies for web scraping and browser tools
RUN python -m playwright install --with-deps chromium || true

# Copy all application codebase into container
COPY . .

# Ensure persistent directories exist
RUN mkdir -p output temp_uploads company_knowledge_base

# Expose ports for Streamlit Command Center (8501) and Arize Phoenix Observability (6060)
EXPOSE 8501 6060

# Default command: launch the Streamlit dashboard
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
