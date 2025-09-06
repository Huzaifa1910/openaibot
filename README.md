# Elite Auto Sales Academy Chat Component

A Streamlit custom component for interacting with the Elite Auto Sales Academy AI assistant.

## Features

- Interactive chat interface
- Command buttons for quick access to sales training topics
- Name personalization
- Mobile-friendly responsive design
- Seamless integration with OpenAI API
- Google Sheets integration for logging

## Getting Started

### Prerequisites

- Python 3.7+
- Streamlit 1.18.0+
- OpenAI API Key

### Installation

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

Create a `.env` file in the project root with:

```
OPENAI_API_KEY=your_openai_api_key
AGBOT_MODEL=gpt-4o
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
DAILY_LOG_SPREADSHEET_ID=your_spreadsheet_id
SESSION_LOG_SPREADSHEET_ID=your_spreadsheet_id
```

### Running the App

```bash
streamlit run app.py
```

The app will be available at http://localhost:8501

## Component Structure

- `app.py` - Main Streamlit application
- `elite_chat_component/frontend/` - Frontend component with HTML, CSS, and JavaScript
- `elite_chat_component/frontend/index.html` - Main component interface

## Using the Chat Component

The chat interface allows users to:

1. Enter their name for personalized training
2. Type messages or questions directly
3. Use command buttons in the sidebar (prefixed with `!`)
4. Track activity with the daily log feature
5. Practice sales scenarios through interactive role-play

## Troubleshooting

If you encounter component timeout errors:

1. Make sure your Streamlit version is up to date
2. Check your browser console for JavaScript errors
3. Verify that the component path in `app.py` points to the correct directory
4. Try restarting the Streamlit server

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

© Elite Auto Sales Academy. All rights reserved.
