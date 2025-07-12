# GitHub Copilot Instructions

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

This is a Python job scraper application with the following characteristics:

## Project Overview
- Web scraping application for job postings
- Uses requests and BeautifulSoup for web scraping
- Command-line interface for managing websites and running scrapes
- Keyword-based job matching
- Outputs results to text files
- Configuration files for websites and keywords

## Code Style Guidelines
- Use type hints for function parameters and return types
- Follow PEP 8 style guidelines
- Include comprehensive error handling for web requests
- Use logging for debugging and monitoring
- Implement rate limiting to be respectful to websites
- Structure code with clear separation of concerns

## Key Features
- Add/remove websites via command line
- Keyword-based job filtering
- Duplicate job detection
- Timestamped output files
- Logging to both console and file
- Session management with proper headers

## Security Considerations
- Use session headers to appear as legitimate browser
- Implement request timeouts
- Handle rate limiting gracefully
- Sanitize URLs and inputs

When suggesting improvements or extensions, consider:
- Adding more sophisticated job detection patterns
- Implementing configurable delay between requests
- Adding support for pagination
- Implementing job deduplication across multiple runs
- Adding export formats (JSON, CSV)
- Integrating with job APIs where available
