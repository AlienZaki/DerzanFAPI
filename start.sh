#!/bin/bash

# Run database migrations before starting the server


# Start the server using Gunicorn
exec gunicorn --bind 0.0.0.0:8000 --timeout 600 derzanBot.wsgi uvicorn.workers.UvicornWorker main:app
