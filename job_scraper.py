#!/usr/bin/env python3
"""
Job Scraper Application

A web scraping application that searches for job positions based on keywords
from a list of websites and outputs results to a text file.
"""

import argparse
import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import json
from urllib.parse import urljoin, urlparse
from datetime import datetime
import os
from typing import List, Dict, Set
import json


class JobScraper:
    def __init__(self, websites_file: str = "websites.txt", keywords_file: str = "keywords.txt", max_links_per_site: int = 10):
        """Initialize the job scraper with configuration files."""
        self.websites_file = websites_file
        self.keywords_file = keywords_file
        self.max_links_per_site = max_links_per_site
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_websites(self) -> List[str]:
        """Load websites from the websites file."""
        websites = []
        try:
            with open(self.websites_file, 'r') as f:
                websites = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except FileNotFoundError:
            self.logger.warning(f"Websites file {self.websites_file} not found. Creating empty file.")
            with open(self.websites_file, 'w') as f:
                f.write("# Add websites to scrape, one per line\n")
                f.write("# Example:\n")
                f.write("# https://example-jobs.com/careers\n")
        return websites

    def load_keywords(self) -> List[str]:
        """Load keywords from the keywords file."""
        keywords = []
        try:
            with open(self.keywords_file, 'r') as f:
                keywords = [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]
        except FileNotFoundError:
            self.logger.warning(f"Keywords file {self.keywords_file} not found. Creating default file.")
            with open(self.keywords_file, 'w') as f:
                f.write("# Add job keywords to search for, one per line\n")
                f.write("# Examples:\n")
                f.write("python\n")
                f.write("software engineer\n")
                f.write("developer\n")
                f.write("data scientist\n")
            keywords = ["python", "software engineer", "developer", "data scientist"]
        return keywords

    def is_job_related_page(self, content: str, keywords: List[str], url: str = "") -> tuple[bool, List[str]]:
        """Check if a page contains job-related content and our keywords."""
        content_lower = content.lower()
        
        # Strong job-related indicators (must have at least one)
        strong_job_indicators = [
            'apply now', 'apply for this position', 'job description', 'requirements', 
            'responsibilities', 'qualifications', 'years of experience', 'submit resume', 
            'cv', 'application', 'candidate', 'hiring', 'employment', 'position details',
            'role description', 'job summary', 'what you\'ll do', 'what you will do',
            'required skills', 'preferred qualifications', 'salary', 'compensation',
            'benefits package', 'location:', 'reports to', 'department:', 'job type',
            'full-time', 'part-time', 'contract', 'permanent', 'temporary'
        ]
        
        # Weak job indicators (supporting evidence)
        weak_job_indicators = [
            'career', 'opportunity', 'role', 'position', 'team', 'join us',
            'remote', 'on-site', 'hybrid', 'office', 'skills', 'experience'
        ]
        
        # Anti-patterns (these suggest it's NOT a job page)
        anti_patterns = [
            'developer tools', 'documentation', 'api reference', 'getting started',
            'tutorials', 'examples', 'download', 'pricing', 'features', 'product',
            'solutions', 'services', 'about us', 'contact us', 'news', 'blog',
            'press release', 'company overview', 'our story', 'mission', 'vision',
            'job search', 'search jobs', 'all jobs', 'job listings', 'browse jobs',
            'filter jobs', 'sort by', 'results found', 'showing', 'page'
        ]
        
        # Check for anti-patterns first
        has_anti_pattern = any(pattern in content_lower for pattern in anti_patterns)
        if has_anti_pattern:
            self.logger.debug("Page rejected due to anti-patterns")
            return False, []
        
        # Check for strong job indicators
        has_strong_indicators = any(indicator in content_lower for indicator in strong_job_indicators)
        
        # Check for weak indicators (need multiple)
        weak_indicator_count = sum(1 for indicator in weak_job_indicators if indicator in content_lower)
        has_weak_indicators = weak_indicator_count >= 2
        
        # Check if our keywords are present
        matched_keywords = [kw for kw in keywords if kw in content_lower]
        
        # Must have keywords AND either strong indicators OR multiple weak indicators
        # But also require at least one very specific job indicator for individual postings
        specific_job_indicators = [
            'apply now', 'apply for this position', 'job description', 'responsibilities',
            'requirements', 'qualifications', 'submit resume', 'submit application'
        ]
        
        has_specific_indicators = any(indicator in content_lower for indicator in specific_job_indicators)
        
        # For a page to be considered a job posting, it needs:
        # 1. Our keywords (at least one)
        # 2. Either strong indicators OR multiple weak indicators  
        # 3. For high-priority job ID URLs, be more lenient since URL suggests it's a job
        is_high_priority_job_url = bool(re.search(r'/jobs?/\d+', url, re.IGNORECASE)) if url else False
        
        if is_high_priority_job_url:
            # For job ID URLs, just need keywords and some job indicators
            is_job_page = len(matched_keywords) > 0 and (has_strong_indicators or has_weak_indicators)
        else:
            # For other URLs, be more strict
            is_job_page = (len(matched_keywords) > 0 and 
                          (has_strong_indicators or has_weak_indicators) and
                          (has_specific_indicators or has_strong_indicators))
        
        self.logger.debug(f"Job page analysis: url={url}, keywords={len(matched_keywords)}, strong_indicators={has_strong_indicators}, weak_indicators={weak_indicator_count}, specific_indicators={has_specific_indicators}, is_job={is_job_page}")
        
        return is_job_page, matched_keywords

    def scrape_website(self, url: str, keywords: List[str]) -> List[Dict[str, str]]:
        """Scrape a single website for job postings matching keywords."""
        jobs = []
        try:
            self.logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # First, try to extract jobs from JavaScript data (for modern job boards)
            jobs_from_js = self.extract_jobs_from_javascript(response.text, url, keywords)
            if jobs_from_js:
                self.logger.info(f"Found {len(jobs_from_js)} jobs from JavaScript data")
                jobs.extend(jobs_from_js)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # First, look for obvious job posting elements on the current page
            job_selectors = [
                '.job-listing', '.job-post', '.position', '.opening',
                '[class*="job"]', '[class*="position"]', '[class*="career"]',
                'article', '.listing', '.vacancy'
            ]
            
            # Check current page content first, but be more selective
            page_content = soup.get_text()
            is_job_page, matched_keywords = self.is_job_related_page(page_content, keywords, url)
            
            # Additional check: avoid treating job listing pages as individual jobs
            listing_page_indicators = [
                'search results', 'filter by', 'sort by', 'results found', 'showing',
                'job listings', 'browse jobs', 'all jobs', 'find jobs', 'job search',
                'total jobs', 'open positions', 'view all', 'more jobs'
            ]
            
            has_listing_indicators = any(indicator in page_content.lower() for indicator in listing_page_indicators)
            
            # Only treat current page as a job if it's job-related AND not a listing page
            if is_job_page and not has_listing_indicators:
                # Current page itself is a job page
                title_element = soup.find(['h1', 'h2']) or soup.find('title')
                title = title_element.get_text(strip=True) if title_element else "Job Posting"
                
                jobs.append({
                    'title': title,
                    'url': url,
                    'source': url,
                    'matched_keywords': matched_keywords
                })
                self.logger.info(f"Current page is a job posting: {title}")
            elif has_listing_indicators:
                self.logger.info(f"Current page appears to be a job listing page, looking for individual jobs")
            
            # Look for job postings in existing elements
            potential_jobs = set()
            for selector in job_selectors:
                elements = soup.select(selector)
                for element in elements:
                    potential_jobs.add(element)
            
            for element in potential_jobs:
                text = element.get_text(strip=True)
                is_job_element, matched_keywords = self.is_job_related_page(text, keywords, url)
                
                if is_job_element:
                    title_element = element.find(['h1', 'h2', 'h3', 'h4', 'a'])
                    title = title_element.get_text(strip=True) if title_element else text[:100]
                    
                    # Try to find a link
                    link_element = element.find('a', href=True)
                    job_url = urljoin(url, link_element.get('href')) if link_element else url
                    
                    jobs.append({
                        'title': title,
                        'url': job_url,
                        'source': url,
                        'matched_keywords': matched_keywords
                    })
            
            # Now look for links that might lead to job pages with smart prioritization
            # First, try to find the main content area to focus our search
            main_content_selectors = [
                'main', '.main', '#main', '.content', '#content', '.main-content',
                '.page-content', '.job-listings', '.jobs', '.positions', '.careers-content',
                'article', '.container', '.wrapper'
            ]
            
            main_content = None
            for selector in main_content_selectors:
                if selector.startswith('.') or selector.startswith('#'):
                    elements = soup.select(selector)
                else:
                    elements = soup.find_all(selector)
                if elements:
                    main_content = elements[0]  # Take the first matching element
                    break
            
            # If we found main content, search within it; otherwise search the whole page
            search_area = main_content if main_content else soup
            all_links = search_area.find_all('a', href=True)
            
            # Categorize links by priority
            high_priority_links = []  # Clear job application links
            medium_priority_links = []  # Job-related links in main content
            low_priority_links = []  # Other potentially relevant links
            
            # Common header/navigation selectors to skip
            header_selectors = [
                'header', 'nav', '.header', '.nav', '.navbar', '.navigation',
                '.menu', '.top-nav', '.main-nav', '.site-header', '.page-header',
                '.breadcrumb', '.breadcrumbs', '.footer', '.site-footer'
            ]
            
            for link in all_links:
                link_text = link.get_text(strip=True).lower()
                href = link.get('href')
                
                # Skip if it's just a fragment, mailto, or external social media links
                if (href.startswith('#') or href.startswith('mailto:') or 
                    'facebook.com' in href or 'twitter.com' in href or 'linkedin.com' in href or
                    'instagram.com' in href or 'youtube.com' in href):
                    continue
                
                # Check if link is in header/navigation area (skip these)
                is_in_header = False
                for selector in header_selectors:
                    if link.find_parent(selector.replace('.', ''), class_=selector.replace('.', '') if '.' in selector else None):
                        is_in_header = True
                        break
                
                if is_in_header:
                    continue
                
                # High priority: Clear application/job detail links
                high_priority_indicators = [
                    'apply now', 'apply for', 'view job', 'job details', 'apply today',
                    'submit application', 'apply here', 'learn more', 'see details',
                    'view position', 'more info'
                ]
                
                # Medium priority: Job-related terms, but prefer specific job URLs
                job_link_indicators = [
                    'job', 'career', 'position', 'opening', 'vacancy', 'hiring',
                    'opportunity', 'role', 'employment'
                ]
                
                # Check for URL patterns that suggest individual job postings
                job_id_patterns = [
                    r'/jobs/\d+', r'/job/\d+', r'/position/\d+', r'/opening/\d+',
                    r'/careers/\d+', r'/opportunity/\d+', r'/role/\d+'
                ]
                
                has_job_id = any(re.search(pattern, href, re.IGNORECASE) for pattern in job_id_patterns)
                
                # Check if it's a high priority link (apply buttons, etc.)
                if any(indicator in link_text for indicator in high_priority_indicators):
                    full_url = urljoin(url, href)
                    high_priority_links.append((full_url, link_text, 'high'))
                
                # Boost priority for links with job IDs (specific job postings)
                elif has_job_id:
                    full_url = urljoin(url, href)
                    high_priority_links.append((full_url, link_text, 'high-jobid'))
                
                # Check if it's a medium priority job-related link
                elif (any(indicator in link_text for indicator in job_link_indicators) or
                      any(indicator in href.lower() for indicator in job_link_indicators)):
                    full_url = urljoin(url, href)
                    medium_priority_links.append((full_url, link_text, 'medium'))
                
                # Check if it contains our keywords (lower priority)
                elif any(keyword in link_text for keyword in keywords):
                    full_url = urljoin(url, href)
                    low_priority_links.append((full_url, link_text, 'low'))
            
            # Combine links by priority, limiting each category
            potential_job_links = []
            
            # Take more high priority links
            potential_job_links.extend(high_priority_links[:max(8, self.max_links_per_site // 2)])
            
            # Fill remaining slots with medium priority
            remaining_slots = self.max_links_per_site - len(potential_job_links)
            if remaining_slots > 0:
                potential_job_links.extend(medium_priority_links[:remaining_slots])
            
            # Fill any remaining slots with low priority
            remaining_slots = self.max_links_per_site - len(potential_job_links)
            if remaining_slots > 0:
                potential_job_links.extend(low_priority_links[:remaining_slots])
            
            self.logger.info(f"Found {len(high_priority_links)} high priority, {len(medium_priority_links)} medium priority, {len(low_priority_links)} low priority links")
            
            # Check each potential job link
            for job_url, link_text, priority in potential_job_links:
                try:
                    self.logger.info(f"Checking {priority} priority job link: {job_url}")
                    time.sleep(0.5)  # Small delay between requests
                    
                    link_response = self.session.get(job_url, timeout=10)
                    link_response.raise_for_status()
                    
                    link_soup = BeautifulSoup(link_response.content, 'html.parser')
                    link_content = link_soup.get_text()
                    
                    is_job_page, matched_keywords = self.is_job_related_page(link_content, keywords, job_url)
                    
                    if is_job_page:
                        # Extract a better title from the job page
                        title_element = link_soup.find(['h1', 'h2']) or link_soup.find('title')
                        title = title_element.get_text(strip=True) if title_element else link_text
                        
                        # Clean up the title
                        title = re.sub(r'\s+', ' ', title).strip()
                        if len(title) > 100:
                            title = title[:100] + "..."
                        
                        jobs.append({
                            'title': title,
                            'url': job_url,
                            'source': url,
                            'matched_keywords': matched_keywords
                        })
                        self.logger.info(f"Found job: {title}")
                
                except requests.RequestException as e:
                    self.logger.debug(f"Could not check link {job_url}: {e}")
                except Exception as e:
                    self.logger.debug(f"Error processing link {job_url}: {e}")
            
            self.logger.info(f"Found {len(jobs)} verified jobs on {url}")
            
        except requests.RequestException as e:
            self.logger.error(f"Error scraping {url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error scraping {url}: {e}")
        
        return jobs

    def scrape_all_websites(self) -> List[Dict[str, str]]:
        """Scrape all websites for job postings."""
        websites = self.load_websites()
        keywords = self.load_keywords()
        
        if not websites:
            self.logger.warning("No websites to scrape. Add websites to websites.txt")
            return []
        
        if not keywords:
            self.logger.warning("No keywords specified. Add keywords to keywords.txt")
            return []
        
        all_jobs = []
        for website in websites:
            jobs = self.scrape_website(website, keywords)
            all_jobs.extend(jobs)
            time.sleep(2)  # Longer delay since we're making more requests per site
        
        # Remove duplicates based on URL
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job['url'] not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job['url'])
        
        return unique_jobs

    def save_results(self, jobs: List[Dict[str, str]], output_file: str = None):
        """Save job search results to a text file."""
        if output_file is None:
            # Ensure job_results directory exists
            os.makedirs("job_results", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"job_results/job_results_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Job Search Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            if not jobs:
                f.write("No jobs found matching your criteria.\n")
                return output_file
            
            for i, job in enumerate(jobs, 1):
                f.write(f"{i}. {job['title']}\n")
                f.write(f"   Source: {job['source']}\n")
                f.write(f"   Apply: {job['url']}\n")
                f.write(f"   Matched Keywords: {', '.join(job['matched_keywords'])}\n")
                f.write("-" * 40 + "\n")
        
        self.logger.info(f"Results saved to {output_file}")
        return output_file

    def add_website(self, website_url: str):
        """Add a new website to the websites list."""
        websites = self.load_websites()
        
        if website_url not in websites:
            with open(self.websites_file, 'a') as f:
                f.write(f"{website_url}\n")
            self.logger.info(f"Added website: {website_url}")
        else:
            self.logger.info(f"Website already exists: {website_url}")

    def remove_website(self, website_url: str):
        """Remove a website from the websites list."""
        websites = self.load_websites()
        
        if website_url in websites:
            websites.remove(website_url)
            with open(self.websites_file, 'w') as f:
                f.write("# Add websites to scrape, one per line\n")
                for website in websites:
                    f.write(f"{website}\n")
            self.logger.info(f"Removed website: {website_url}")
        else:
            self.logger.info(f"Website not found: {website_url}")

    def list_websites(self):
        """List all configured websites."""
        websites = self.load_websites()
        print("\nConfigured websites:")
        if websites:
            for i, website in enumerate(websites, 1):
                print(f"{i}. {website}")
        else:
            print("No websites configured.")
        print()

    def extract_jobs_from_javascript(self, html_content: str, source_url: str, keywords: List[str]) -> List[Dict[str, str]]:
        """Extract job data from JavaScript variables in modern job boards."""
        jobs = []
        
        try:
            # Look for common patterns in job board JavaScript
            js_patterns = [
                # Qualtrics/Phenom pattern
                r'phApp\.ddo\s*=\s*({.*?});',
                # General JSON data patterns
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'window\.jobData\s*=\s*({.*?});',
                r'window\.jobs\s*=\s*(\[.*?\]);',
                # Looking for job arrays in various formats
                r'"jobs"\s*:\s*(\[.*?\])',
                r'"jobListings"\s*:\s*(\[.*?\])',
                # Greenhouse.io pattern
                r'window\.gon\s*=\s*({.*?});',
                # Lever.co pattern
                r'window\.INITIAL_STATE\s*=\s*({.*?});',
                # BambooHR pattern
                r'window\.APP_STATE\s*=\s*({.*?});',
                # Workday pattern
                r'var\s+wdAppInstanceData\s*=\s*({.*?});',
                # Indeed pattern
                r'window\.mosaic\.providerData\s*=\s*({.*?});',
            ]
            
            for pattern in js_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    try:
                        # Try to parse as JSON
                        data = json.loads(match)
                        jobs_extracted = self.extract_jobs_from_json_data(data, source_url, keywords)
                        if jobs_extracted:
                            jobs.extend(jobs_extracted)
                            self.logger.info(f"Extracted {len(jobs_extracted)} jobs from JavaScript pattern")
                            break  # Stop after first successful extraction
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.debug(f"Failed to parse JavaScript data: {e}")
                        continue
                        
            # Also look for JSON-LD structured data (common in job sites)
            jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            jsonld_matches = re.findall(jsonld_pattern, html_content, re.DOTALL | re.IGNORECASE)
            for match in jsonld_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                        # Single job posting
                        title = data.get('title', 'Unknown Position')
                        apply_url = ''
                        if 'directApply' in data:
                            apply_url = data['directApply']
                        elif 'url' in data:
                            apply_url = data['url']
                        
                        if apply_url:
                            job_text = f"{title} {data.get('description', '')}"
                            matched_keywords = []
                            for keyword in keywords:
                                if keyword.lower() in job_text.lower():
                                    matched_keywords.append(keyword)
                            
                            if matched_keywords:
                                jobs.append({
                                    'title': title,
                                    'url': apply_url,
                                    'source': source_url,
                                    'matched_keywords': matched_keywords
                                })
                except json.JSONDecodeError:
                    continue
        
        except Exception as e:
            self.logger.debug(f"Error extracting jobs from JavaScript: {e}")
        
        return jobs
    
    def extract_jobs_from_json_data(self, data: dict, source_url: str, keywords: List[str]) -> List[Dict[str, str]]:
        """Extract job data from parsed JSON data."""
        jobs = []
        
        try:
            # Handle Qualtrics/Phenom structure
            if 'eagerLoadRefineSearch' in data and 'data' in data['eagerLoadRefineSearch']:
                job_data = data['eagerLoadRefineSearch']['data']
                if 'jobs' in job_data:
                    for job in job_data['jobs']:
                        title = job.get('title', 'Unknown Position')
                        job_url = job.get('applyUrl', '')
                        if not job_url:
                            job_url = f"{source_url.split('/c/')[0]}/job/{job.get('jobId', '')}"
                        
                        # Check if job matches keywords - be more lenient for JavaScript-extracted jobs
                        job_text = f"{title} {job.get('descriptionTeaser', '')} {job.get('category', '')}"
                        
                        # For JavaScript-extracted jobs, we're more lenient since they're already from a relevant category
                        matched_keywords = []
                        for keyword in keywords:
                            if keyword.lower() in job_text.lower():
                                matched_keywords.append(keyword)
                        
                        # If we're on a category page, jobs are already filtered, so we should include them
                        # even if they don't explicitly match our keywords
                        if matched_keywords or '/c/' in source_url:
                            if not matched_keywords:
                                matched_keywords = ['relevant category']
                            
                            jobs.append({
                                'title': title,
                                'url': job_url,
                                'source': source_url,
                                'matched_keywords': matched_keywords
                            })
            
            # Handle Greenhouse.io structure
            elif 'gon' in data or 'departments' in data:
                departments = data.get('departments', [])
                for dept in departments:
                    if 'jobs' in dept:
                        for job in dept['jobs']:
                            title = job.get('title', 'Unknown Position')
                            job_url = job.get('absolute_url', '')
                            if job_url and not job_url.startswith('http'):
                                job_url = f"https://boards.greenhouse.io{job_url}"
                            
                            if job_url:
                                job_text = f"{title} {job.get('content', '')}"
                                matched_keywords = []
                                for keyword in keywords:
                                    if keyword.lower() in job_text.lower():
                                        matched_keywords.append(keyword)
                                
                                if matched_keywords:
                                    jobs.append({
                                        'title': title,
                                        'url': job_url,
                                        'source': source_url,
                                        'matched_keywords': matched_keywords
                                    })
            
            # Handle Lever.co structure
            elif 'postings' in data:
                for job in data['postings']:
                    title = job.get('text', 'Unknown Position')
                    job_url = job.get('hostedUrl', '')
                    
                    if job_url:
                        job_text = f"{title} {job.get('description', '')}"
                        matched_keywords = []
                        for keyword in keywords:
                            if keyword.lower() in job_text.lower():
                                matched_keywords.append(keyword)
                        
                        if matched_keywords:
                            jobs.append({
                                'title': title,
                                'url': job_url,
                                'source': source_url,
                                'matched_keywords': matched_keywords
                            })
            
            # Handle other potential structures
            elif 'jobs' in data:
                job_list = data['jobs']
                if isinstance(job_list, list):
                    for job in job_list:
                        if isinstance(job, dict):
                            title = job.get('title', job.get('name', job.get('jobTitle', 'Unknown Position')))
                            job_url = job.get('url', job.get('link', job.get('applyUrl', job.get('applicationUrl', ''))))
                            
                            if job_url:
                                job_text = f"{title} {job.get('description', job.get('summary', ''))}"
                                matched_keywords = []
                                for keyword in keywords:
                                    if keyword.lower() in job_text.lower():
                                        matched_keywords.append(keyword)
                                
                                if matched_keywords:
                                    jobs.append({
                                        'title': title,
                                        'url': job_url,
                                        'source': source_url,
                                        'matched_keywords': matched_keywords
                                    })
        
        except Exception as e:
            self.logger.debug(f"Error processing JSON job data: {e}")
        
        return jobs

def main():
    parser = argparse.ArgumentParser(description="Job Scraper - Find job postings matching your skills")
    parser.add_argument('--scrape', action='store_true', help='Run the scraper')
    parser.add_argument('--add-website', metavar='URL', help='Add a website to scrape')
    parser.add_argument('--remove-website', metavar='URL', help='Remove a website from scraping')
    parser.add_argument('--list-websites', action='store_true', help='List all configured websites')
    parser.add_argument('--output', metavar='FILE', help='Output file for results')
    parser.add_argument('--max-links', type=int, default=10, metavar='N', 
                       help='Maximum number of links to check per website (default: 10)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging for debugging')
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        # Also set the handlers to debug level
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)
    
    scraper = JobScraper(max_links_per_site=args.max_links)
    
    if args.add_website:
        scraper.add_website(args.add_website)
    elif args.remove_website:
        scraper.remove_website(args.remove_website)
    elif args.list_websites:
        scraper.list_websites()
    elif args.scrape:
        jobs = scraper.scrape_all_websites()
        output_file = scraper.save_results(jobs, args.output)
        print(f"\nScraping complete! Found {len(jobs)} jobs.")
        print(f"Results saved to: {output_file}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
