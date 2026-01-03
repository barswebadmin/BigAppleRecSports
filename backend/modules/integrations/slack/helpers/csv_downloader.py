"""
Slack-specific CSV downloading utilities.

Handles downloading CSV files from Slack private URLs using bearer token authentication.
"""
import logging
from typing import Optional, List
import requests
from slack_sdk import WebClient

from shared.csv import parse_csv_text

logger = logging.getLogger(__name__)


def download_and_parse_csv(url: str, client: WebClient) -> Optional[List[List[str]]]:
    """
    Download a CSV file from a Slack private URL and parse it.
    
    Args:
        url: Slack private URL to the CSV file
        client: Initialized Slack WebClient with valid token
        
    Returns:
        List of rows, where each row is a list of cell values, or None if download/parse fails
        
    Example:
        client = WebClient(token="xoxb-...")
        csv_data = download_and_parse_csv(file_url, client)
        if csv_data:
            for row in csv_data:
                print(row)
    """
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {client.token}"},
            timeout=10
        )
        response.raise_for_status()
        content = response.content.decode("utf-8")
        return parse_csv_text(content)
    except requests.RequestException as e:
        logger.error(f"Error downloading CSV from {url}: {e}")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"Error decoding CSV content: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading/parsing CSV: {e}", exc_info=True)
        return None

