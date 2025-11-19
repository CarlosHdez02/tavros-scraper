# ================================
# Base image with Playwright + deps
# ================================
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

# Create app directory
WORKDIR /app

# Copy project files
COPY . .

# Create logs directory to avoid FileNotFoundError
RUN mkdir -p logs

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN playwright install chromium

# Install supervisor to run multiple processes
RUN apt-get update && apt-get install -y supervisor

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose your API server port (modify if needed)
EXPOSE 5000

# Start supervisor (which starts both API + scraper)
CMD ["/usr/bin/supervisord"]
