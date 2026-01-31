#!/bin/bash
# Script to run the Brazil news collector

# Change to the correct directory
cd /Users/mac/Documents/GitHub/zero-times.github.io

# Install required Python packages if not already installed
pip3 install requests beautifulsoup4 feedparser || pip install requests beautifulsoup4 feedparser

# Run the news collector script
python3 scripts/collect_brazil_news.py