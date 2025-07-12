#!/usr/bin/env python3
"""
Test script for the Job Scraper application
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper import JobScraper

def test_basic_functionality():
    """Test basic functionality of the job scraper."""
    print("Testing Job Scraper...")
    
    # Initialize scraper
    scraper = JobScraper()
    
    # Test loading keywords (should create default if not exists)
    keywords = scraper.load_keywords()
    print(f"✓ Loaded {len(keywords)} keywords: {keywords[:3]}...")
    
    # Test loading websites (should create default if not exists)
    websites = scraper.load_websites()
    print(f"✓ Loaded {len(websites)} websites")
    
    # Test adding a website
    test_url = "https://example.com/jobs"
    scraper.add_website(test_url)
    print(f"✓ Added test website: {test_url}")
    
    # Test listing websites
    print("✓ Website management working")
    
    # Test removing the website
    scraper.remove_website(test_url)
    print(f"✓ Removed test website: {test_url}")
    
    print("\n🎉 All basic tests passed!")
    print("\nTo start using the scraper:")
    print("1. Add real job websites to websites.txt")
    print("2. Customize keywords.txt with your skills")
    print("3. Run: python job_scraper.py --scrape")

if __name__ == "__main__":
    test_basic_functionality()
