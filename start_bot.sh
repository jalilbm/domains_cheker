#!/bin/bash

# Check if the lock file exists
if [ -f /tmp/start_bot.lock ]; then
    exit 1
fi

# Create the lock file
touch /tmp/start_bot.lock

# # Change to the bot directory
# cd /path/to/bot

# Start the bot
/usr/local/bin/python3.9 /home/ec2-user/domains_checker/telegram_bot.py

# Remove the lock file
rm /tmp/start_bot.lock