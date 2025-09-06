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

2. Set up credentials:

#### Option A: Local Development with Streamlit Secrets (Recommended)

Create a `.streamlit/secrets.toml` file in the project root:

```toml
# .streamlit/secrets.toml

# Google Service Account
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "xxxxxxxxxxxxxxxxxxxx"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-sa@your-project.iam.gserviceaccount.com"
client_id = "1234567890"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-sa%40your-project.iam.gserviceaccount.com"

# Spreadsheet IDs
DAILY_LOG_SPREADSHEET_ID = "your-daily-log-spreadsheet-id"
SESSION_LOG_SPREADSHEET_ID = "your-session-log-spreadsheet-id"

# OpenAI
OPENAI_API_KEY = "your_openai_api_key"
```

#### Option B: Environment Variables

As an alternative, you can set environment variables by creating a `.env` file:

```
OPENAI_API_KEY=your_openai_api_key
AGBOT_MODEL=gpt-4o
GOOGLE_SERVICE_ACCOUNT_JSON='{...json content of your service account file...}'
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

## Deployment

### Deploying to Streamlit Community Cloud

1. Push your code to GitHub
2. Connect your GitHub repository to Streamlit Community Cloud
3. Add your secrets in the Streamlit dashboard:
   - Go to your app settings
   - Click on "Secrets"
   - Add your service account JSON and other secrets
4. Deploy your app

## Troubleshooting

If you encounter component timeout errors:

1. Make sure your Streamlit version is up to date
2. Check your browser console for JavaScript errors
3. Verify that the component path in `app.py` points to the correct directory
4. Try restarting the Streamlit server

### Authentication Issues

If you're having trouble with Google Sheets authentication:

1. Make sure your service account JSON is correctly formatted in secrets.toml
2. Check that you've shared your Google Sheets with the service account email
3. Verify that the service account has appropriate permissions
4. Check for error messages in the terminal/console output

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

© Elite Auto Sales Academy. All rights reserved.
