#!/bin/bash
# Azure App Service runs this as the startup command.
# Set this in: App Service > Configuration > General Settings > Startup Command
#   bash startup.sh

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
