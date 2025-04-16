import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from typing import List, Dict
import time
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API configuration
API_KEY = 'YOUTUBE API KEY'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
MIN_CHANNELS_REQUIRED = 50  # Target number of channels
EXCEL_FILE = os.path.join(os.getcwd(), 'new_youtube_channels.xlsx')
DAYS_TO_SEARCH = 90  # Search last 90 days for more recent channels
MAX_RESULTS_PER_PAGE = 50  # Maximum results per API call

def verify_excel_file():
    """Verify that the Excel file exists and is accessible."""
    try:
        if os.path.exists(EXCEL_FILE):
            logger.info(f"Excel file exists at: {EXCEL_FILE}")
            return True
        else:
            logger.info(f"Excel file will be created at: {EXCEL_FILE}")
            return False
    except Exception as e:
        logger.error(f"Error checking Excel file: {e}")
        return False

def get_youtube_service():
    """Create and return a YouTube API service object."""
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)

def search_recent_videos(youtube, max_results: int = MAX_RESULTS_PER_PAGE, page_token: str = None) -> tuple[List[Dict], str]:
    """
    Search for recent videos to find new channels.
    Returns a tuple of (list of video items, next page token).
    """
    try:
        # Calculate the date X days ago
        days_ago = (datetime.now() - timedelta(days=DAYS_TO_SEARCH)).strftime('%Y-%m-%dT%H:%M:%SZ')
        logger.info(f"Searching for videos published after: {days_ago}")
        
        # Search for videos published in the last X days
        search_response = youtube.search().list(
            q='',  # Empty query to get trending/viral content
            part='snippet',
            maxResults=max_results,
            type='video',
            regionCode='US',
            publishedAfter=days_ago,
            order='date',
            pageToken=page_token
        ).execute()

        items = search_response.get('items', [])
        next_page_token = search_response.get('nextPageToken')
        logger.info(f"Found {len(items)} recent videos")
        return items, next_page_token
    except HttpError as e:
        logger.error(f'An HTTP error occurred while searching videos: {e}')
        return [], None

def parse_date(date_str: str) -> datetime:
    """Parse date string from YouTube API, handling microseconds."""
    try:
        # Remove microseconds if present
        if '.' in date_str:
            date_str = date_str.split('.')[0] + 'Z'
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError as e:
        logger.error(f"Error parsing date {date_str}: {e}")
        return None

def get_channel_info(youtube, channel_id: str) -> Dict:
    """Get detailed information about a channel."""
    try:
        logger.info(f"Fetching information for channel: {channel_id}")
        channel_response = youtube.channels().list(
            part='snippet,statistics',
            id=channel_id
        ).execute()

        if not channel_response.get('items'):
            logger.warning(f"No channel information found for ID: {channel_id}")
            return None

        channel = channel_response['items'][0]
        published_at = channel['snippet']['publishedAt']
        channel_created = parse_date(published_at)
        
        if not channel_created:
            return None

        channel_info = {
            'channel_id': channel_id,
            'title': channel['snippet']['title'],
            'description': channel['snippet']['description'],
            'published_at': published_at,
            'subscriber_count': int(channel['statistics']['subscriberCount']),
            'url': f'https://www.youtube.com/channel/{channel_id}'
        }
        
        logger.info(f"Channel '{channel_info['title']}' created at: {published_at}")
        return channel_info
    except HttpError as e:
        logger.error(f'An HTTP error occurred while fetching channel info: {e}')
        return None
    except KeyError as e:
        logger.error(f'Missing key in channel response: {e}')
        return None

def append_to_excel(channel_info: Dict):
    """Append a single channel to the Excel file."""
    try:
        logger.info(f"Attempting to write channel '{channel_info['title']}' to Excel file")
        
        # Create DataFrame for the new channel
        new_df = pd.DataFrame([channel_info])
        
        # Try to read existing Excel file
        try:
            if os.path.exists(EXCEL_FILE):
                logger.info(f"Reading existing Excel file: {EXCEL_FILE}")
                existing_df = pd.read_excel(EXCEL_FILE)
                # Combine existing data with new data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                logger.info("No existing Excel file found, creating new one")
                combined_df = new_df
        except Exception as e:
            logger.error(f"Error reading existing Excel file: {e}")
            combined_df = new_df
        
        # Sort by subscriber count
        combined_df = combined_df.sort_values('subscriber_count', ascending=False)
        
        # Write to Excel with formatting
        logger.info(f"Writing to Excel file: {EXCEL_FILE}")
        with pd.ExcelWriter(EXCEL_FILE, engine='xlsxwriter') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='New Channels')
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['New Channels']
            
            # Add hyperlink format
            link_format = workbook.add_format({
                'color': 'blue',
                'underline': True
            })
            
            # Apply hyperlink format to URL column
            worksheet.set_column('F:F', 50, link_format)
        
        # Verify file was created
        if os.path.exists(EXCEL_FILE):
            file_size = os.path.getsize(EXCEL_FILE)
            logger.info(f"Successfully wrote to Excel file. File size: {file_size} bytes")
        else:
            logger.error("Excel file was not created successfully")
            
    except Exception as e:
        logger.error(f"Error updating Excel file: {e}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Attempted to write to: {EXCEL_FILE}")

def is_recent_channel(channel_created: datetime) -> bool:
    """Check if a channel was created within the last 6 months."""
    six_months_ago = datetime.now() - timedelta(days=180)
    return channel_created >= six_months_ago

def main():
    logger.info("Starting YouTube Growth Tracker script")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Excel file will be saved to: {EXCEL_FILE}")
    
    # Verify Excel file path
    verify_excel_file()
    
    youtube = get_youtube_service()
    processed_channels = set()
    next_page_token = None
    pages_processed = 0
    max_pages = 100  # Increased max pages to find more channels
    channels_found = 0
    retry_count = 0
    max_retries = 3

    while channels_found < MIN_CHANNELS_REQUIRED and pages_processed < max_pages:
        pages_processed += 1
        logger.info(f"Processing page {pages_processed}")
        
        # Get recent videos with pagination
        videos, next_page_token = search_recent_videos(youtube, page_token=next_page_token)
        
        if not videos:
            if retry_count < max_retries:
                retry_count += 1
                logger.warning(f"No videos found, retrying... (Attempt {retry_count}/{max_retries})")
                time.sleep(5)  # Wait before retrying
                continue
            else:
                logger.warning("No more videos found after retries")
                break
        
        retry_count = 0  # Reset retry count on successful video fetch
        
        # Process each video to get channel information
        for video in videos:
            channel_id = video['snippet']['channelId']
            
            # Skip if we've already processed this channel
            if channel_id in processed_channels:
                logger.debug(f"Skipping already processed channel: {channel_id}")
                continue
                
            processed_channels.add(channel_id)
            
            # Get channel information
            channel_info = get_channel_info(youtube, channel_id)
            
            if channel_info:
                # Check if channel was created within the last 6 months
                channel_created = parse_date(channel_info['published_at'])
                
                if channel_created and is_recent_channel(channel_created):
                    logger.info(f"Adding channel '{channel_info['title']}' to results")
                    append_to_excel(channel_info)
                    channels_found += 1
                    logger.info(f"Found {channels_found}/{MIN_CHANNELS_REQUIRED} required channels")
                else:
                    logger.info(f"Channel '{channel_info['title']}' was created too long ago")
            
            # Sleep to avoid hitting API quota limits
            time.sleep(0.5)
        
        if not next_page_token:
            if retry_count < max_retries:
                retry_count += 1
                logger.warning(f"No next page token, retrying... (Attempt {retry_count}/{max_retries})")
                time.sleep(5)  # Wait before retrying
                continue
            else:
                logger.info("No more pages to process after retries")
                break

    logger.info(f"Script completed. Found {channels_found} channels matching criteria.")
    logger.info(f"Excel file location: {EXCEL_FILE}")

if __name__ == '__main__':
    main() 