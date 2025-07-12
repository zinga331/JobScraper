# JobScraper
Leveraging help from AI to write a job scrapper to web scrap the job listings of different companies and return urls for ones that might fit my needs. WIP.
## Features

- **Web Scraping**: Scrape multiple job websites for positions
- **Keyword Matching**: Find jobs that match your specified skills and keywords
- **Command Line Interface**: CLI for managing websites and running scrapes
- **Configuration Files**: Maintain website lists and keywords in text files
- **Output Management**: Results saved to timestamped text files with job details and application links
- **Logging**: Comprehensive logging for monitoring and debugging
- **Duplicate Detection**: Automatically removes duplicate job postings

## Installation

1. Clone or download this project
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

### Adding Websites to Scrape

Add websites to the `websites.txt` file, one URL per line:

```bash
python job_scraper.py --add-website "https://example-jobs.com/careers"
```

Or edit `websites.txt` directly:
```
https://jobs.github.com/
https://stackoverflow.com/jobs
https://www.python.org/jobs/
```

### Setting Up Keywords

Edit the `keywords.txt` file to include skills and job titles you're interested in:
```
python
software engineer
data scientist
machine learning
backend developer
```

## Usage

### Run the Job Scraper

```bash
python job_scraper.py --scrape
```

This will:
- Read websites from `websites.txt`
- Read keywords from `keywords.txt`
- Scrape each website for job postings
- Match jobs against your keywords
- Save results to a timestamped file (e.g., `job_results_20250105_143022.txt`)

### Manage Websites

List configured websites:
```bash
python job_scraper.py --list-websites
```

Add a new website:
```bash
python job_scraper.py --add-website "https://new-job-site.com/careers"
```

Remove a website:
```bash
python job_scraper.py --remove-website "https://old-job-site.com/careers"
```

### Specify Output File

```bash
python job_scraper.py --scrape --output "my_job_search.txt"
```

## Output Format

Results are saved in text format with the following information for each job:
- Job title
- Source website
- Application URL
- Matched keywords

Example output:
```
Job Search Results - 2025-01-05 14:30:22
============================================================

1. Senior Python Developer
   Source: https://jobs.example.com/
   Apply: https://jobs.example.com/apply/12345
   Matched Keywords: python, developer

2. Data Scientist - Machine Learning
   Source: https://careers.example.com/
   Apply: https://careers.example.com/positions/67890
   Matched Keywords: data scientist, machine learning
```

## Project Structure

```
JobScraper/
├── job_scraper.py          # Main application
├── requirements.txt        # Python dependencies
├── websites.txt           # List of websites to scrape
├── keywords.txt           # Job keywords and skills
├── README.md             # This file
├── scraper.log           # Application logs (created when running)
├── job_results_*.txt     # Output files (created when scraping)
└── .github/
    └── copilot-instructions.md  # GitHub Copilot configuration
```

## How It Works

1. **Website Loading**: Reads websites from `websites.txt`
2. **Keyword Loading**: Reads search keywords from `keywords.txt`
3. **Web Scraping**: For each website:
   - Sends HTTP request with browser-like headers
   - Parses HTML content using BeautifulSoup
   - Looks for job-related elements and links
   - Matches content against keywords
4. **Results Processing**: 
   - Removes duplicate jobs based on URLs
   - Formats results with job details
   - Saves to timestamped output file

## Customization

### Adding New Job Site Patterns

The scraper uses common CSS selectors to find job postings. You can extend the `job_selectors` list in the `scrape_website` method to support specific job sites better:

```python
job_selectors = [
    '.job-listing', '.job-post', '.position', '.opening',
    '[class*="job"]', '[class*="position"]', '[class*="career"]',
    # Add site-specific selectors here
]
```

### Rate Limiting

The scraper includes a 1-second delay between requests to be respectful to websites. You can adjust this in the `scrape_all_websites` method.

## Limitations

- **Generic Scraping**: Uses general patterns that may not work perfectly on all job sites
- **Rate Limiting**: Some sites may block rapid requests
- **JavaScript**: Cannot scrape sites that load content dynamically with JavaScript
- **Authentication**: Cannot access sites requiring login

## Future Enhancements

- **AI Integration**: Use AI models for better job relevance scoring
- **API Integration**: Support for job board APIs (Indeed, LinkedIn, etc.)
- **Advanced Filtering**: Location, salary, experience level filters
- **Email Notifications**: Automatic alerts for new matching jobs
- **Database Storage**: Store results in a database for historical tracking
- **Web Interface**: Optional web UI for easier management

## Legal and Ethical Considerations

- **Respect robots.txt**: Check website policies before scraping
- **Rate Limiting**: Don't overload websites with requests
- **Terms of Service**: Ensure compliance with website terms
- **Personal Use**: This tool is designed for personal job searching

## Troubleshooting

### No Jobs Found
- Check that websites in `websites.txt` are accessible
- Verify keywords in `keywords.txt` are relevant
- Check `scraper.log` for error messages

### Blocked Requests
- Some sites may block automated requests
- Try adding delays between requests
- Consider using proxy services for large-scale scraping

### Dependencies Issues
```bash
pip install --upgrade -r requirements.txt
```

## License

This project is for educational and personal use. Please respect website terms of service and applicable laws when using this tool.