#!/bin/bash
 
# Start the Telegram bot with Gunicorn
echo "Starting Telegram Comment Ban Bot with Gunicorn..."
exec gunicorn --config gunicorn.conf.py bot:app 