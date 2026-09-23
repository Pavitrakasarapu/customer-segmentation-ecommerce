"""
Gunicorn production server configuration.
Automatically configures port, workers, threads, and timeouts.
"""
import os

# Port binding: Use Render's PORT environment variable, default to 5000
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Concurrency
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = int(os.environ.get("PYTHON_GET_THREADS", 4))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
