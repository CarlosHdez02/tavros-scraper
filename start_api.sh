#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start API server
python api_server.py


# ========================================
# Environment Variables (.env file)
# ========================================
# PORT=5000                    # Backend API port (default: 5000)
# FRONTEND_PORT=3000           # Frontend port for CORS whitelist (default: 3000)
# FRONTEND_URL=http://localhost:3000  # Full frontend URL (optional, auto-generated from FRONTEND_PORT)
# PRODUCTION_FRONTEND_URL=https://yourdomain.com  # Production frontend URL (optional)