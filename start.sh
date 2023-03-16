#!/bin/bash

# Run database migrations before starting the server


# Start the server using Gunicorn
#exec gunicorn main:app --bind 0.0.0.0:8000 --timeout 600
exec gunicorn main:app --workers 4 --bind 0.0.0.0:8000 --timeout 600 --worker-class uvicorn.workers.UvicornWorker