import json
import requests
import gzip
import io
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import boto3
import os
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
MAX_CONTENT_SIZE = int(os.environ.get('MAX_CONTENT_SIZE', 1024 * 1024))  # 1MB default
TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))  # 30 seconds default

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for web scraping functionality.
    This function will be registered as a Bedrock tool.
    """
    # Log the incoming event for debugging
    logger.info(f"Received event: {json.dumps(event, indent=2)}")
    logger.info(f"Context: request_id={context.aws_request_id}, function_name={context.function_name}")

    try:
        # Parse the input from Bedrock Agent
        input_data = event.get('inputText', '')
        request_body = event.get('requestBody', {})

        logger.info(f"Input data: {input_data}")
        logger.info(f"Request body: {request_body}")

        # Extract URL from different possible input formats
        url = None
        if isinstance(request_body, dict):
            url = request_body.get('url') or request_body.get('website_url')

        if not url and input_data:
            # Try to extract URL from input text
            url = extract_url_from_text(input_data)

        logger.info(f"Extracted URL: {url}")

        if not url:
            response = create_error_response("No valid URL provided. Please provide a URL to scrape.")
            logger.info(f"Returning error response (no URL): {json.dumps(response, indent=2)}")
            return response

        # Validate URL
        if not is_valid_url(url):
            response = create_error_response(f"Invalid URL format: {url}")
            logger.info(f"Returning error response (invalid URL): {json.dumps(response, indent=2)}")
            return response

        logger.info(f"Starting to scrape URL: {url}")

        # Perform web scraping
        scraped_content = scrape_website(url)

        logger.info(f"Scraping result: success={scraped_content.get('success')}")
        if scraped_content.get('success'):
            logger.info(f"Scraped content length: {scraped_content.get('content_length', 0)} characters")
            logger.info(f"Title: {scraped_content.get('title', 'N/A')}")
        else:
            logger.error(f"Scraping failed: {scraped_content.get('error')}")

        response = create_success_response(scraped_content)
        logger.info(f"Final response being returned: {json.dumps(response, indent=2)}")
        return response

    except Exception as e:
        logger.exception(f"Unexpected error in lambda_handler: {str(e)}")
        response = create_error_response(f"Error scraping website: {str(e)}")
        logger.info(f"Returning exception response: {json.dumps(response, indent=2)}")
        return response

def extract_url_from_text(text: str) -> str:
    """Extract URL from input text."""
    import re
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    matches = re.findall(url_pattern, text)
    return matches[0] if matches else None

def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def scrape_website(url: str) -> Dict[str, Any]:
    """
    Main web scraping function with proper error handling.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        # Make request with proper error handling
        response = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True
        )
        response.raise_for_status()

        # Check content size
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > MAX_CONTENT_SIZE:
            return {
                'success': False,
                'error': f'Content too large: {content_length} bytes (max: {MAX_CONTENT_SIZE})'
            }

        # Handle content properly - collect as bytes first
        content_bytes = b''
        total_size = 0

        for chunk in response.iter_content(chunk_size=8192):
            total_size += len(chunk)
            if total_size > MAX_CONTENT_SIZE:
                return {
                    'success': False,
                    'error': f'Content too large: exceeded {MAX_CONTENT_SIZE} bytes'
                }
            content_bytes += chunk

        # Handle gzip decompression if needed
        if response.headers.get('content-encoding') == 'gzip':
            try:
                content_bytes = gzip.decompress(content_bytes)
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to decompress gzip content: {str(e)}'
                }

        # Decode to string
        try:
            content = content_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to decode content: {str(e)}'
            }

        # Parse and clean HTML
        soup = BeautifulSoup(content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()

        # Extract text content
        text_content = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = ' '.join(chunk for chunk in chunks if chunk)

        # Limit text length
        if len(clean_text) > 10000:  # Limit to 10k characters for processing
            clean_text = clean_text[:10000] + "... [content truncated]"

        # Extract metadata
        title = soup.find('title')
        title_text = title.string.strip() if title else "No title found"

        meta_description = soup.find('meta', attrs={'name': 'description'})
        description = meta_description.get('content', '') if meta_description else ''

        return {
            'success': True,
            'url': url,
            'title': title_text,
            'description': description,
            'content': clean_text,
            'content_length': len(clean_text),
            'final_url': response.url  # In case of redirects
        }

    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': f'Request timeout after {TIMEOUT} seconds'
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Request failed: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Parsing error: {str(e)}'
        }

def create_success_response(scraped_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create successful response for Bedrock Agent."""
    logger.info(f"Creating success response for scraped_data: {scraped_data.get('success')}")

    if scraped_data.get('success'):
        response_text = f"""Successfully scraped: {scraped_data['title']}
URL: {scraped_data['url']}
Content length: {scraped_data['content_length']} characters

Content:
{scraped_data['content']}"""
    else:
        response_text = f"Failed to scrape website: {scraped_data.get('error', 'Unknown error')}"

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'response': {
                'actionGroup': 'web_scrape',
                'function': 'scrape_website',
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            'body': response_text
                        }
                    }
                }
            }
        })
    }

    logger.info(f"Created response structure: {json.dumps(response, indent=2)}")
    return response

def create_error_response(error_message: str) -> Dict[str, Any]:
    """Create error response for Bedrock Agent."""
    logger.error(f"Creating error response: {error_message}")

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'response': {
                'actionGroup': 'web_scrape',
                'function': 'scrape_website',
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            'body': f"Error: {error_message}"
                        }
                    }
                }
            }
        })
    }

    logger.info(f"Created error response structure: {json.dumps(response, indent=2)}")
    return response
