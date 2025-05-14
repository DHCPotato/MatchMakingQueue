#!/bin/bash


# Change to the project directory
cd /var/www/scripts || exit

# Ensure Python dependencies are installed
pip3 install --user requests

# Infinite loop to execute script every 15 seconds
while true; do
    # Run the Python script (WITH absolute path)
    python3 /var/www/scripts/extract_excel_data.py

    # Ensure the JSON file exists and has correct permissions
    chmod 777 /var/www/html/table_data.json

    # Wait 15 seconds before running again
    sleep 15
done
