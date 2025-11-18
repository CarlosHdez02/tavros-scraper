# Use Playwright base image (includes Chrome, Firefox, WebKit, deps)
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# (Optional) Ensure logs folder exists
RUN mkdir -p logs

# Expose no ports since it's a worker
CMD ["python", "main_checkin.py"]
