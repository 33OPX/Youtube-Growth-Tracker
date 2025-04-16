# YouTube Channel Finder

A Python script that uses the YouTube Data API to find and track new YouTube channels. The script searches for recent channels and monitors their growth.

## Features

- Finds channels created within the last 6 months
- Tracks subscriber counts
- Exports results to Excel with clickable channel links
- Handles API pagination and rate limiting
- Automatic retry mechanism for API calls

## Requirements

- Python 3.7+
- YouTube Data API key
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/YouTube-Growth-Tracker.git
cd YouTube Growth Tracker
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up your YouTube API key:
   - Get an API key from the [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the YouTube Data API v3
   - Replace the API_KEY in the script with your key

## Usage

Run the script:
```bash
python "YouTube Growth Tracker.py"
```

The script will:
1. Search for recent videos
2. Extract channel information
3. Filter for channels created in the last 6 months
4. Save results to 'new_youtube_channels.xlsx'

## Output

The script generates an Excel file containing:
- Channel title
- Description
- Creation date
- Subscriber count
- Direct link to the channel

## License

MIT License

## Contributing

Feel free to submit issues and pull requests. 
