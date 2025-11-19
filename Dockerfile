# ================================
# Base image with Playwright + deps
# ================================
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

# Create app directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN playwright install chromium

# Install supervisor to run multiple processes
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose your API server port (modify if needed)
EXPOSE 5000

# Start supervisor (which starts both API + scraper)
# Create logs directory at runtime in case working directory changes
CMD mkdir -p logs && /usr/bin/supervisord