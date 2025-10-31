#!/bin/bash

# Start script for Telegram Attention Bot
# This script should be run from the project root directory

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables from .env file if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the bot
python main.py
