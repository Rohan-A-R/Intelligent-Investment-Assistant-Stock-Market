# Intelligent Investment Assistant

A Django-based web application for stock market analysis and sentiment analysis.

## Features

- Stock market data analysis
- Sentiment analysis using Gemini AI
- News integration
- Google OAuth2 authentication
- Portfolio management
- Reddit integration

## Setup Instructions

1. Clone the repository:
```bash
git clone <repository-url>
cd stock
```

2. Create and activate a virtual environment:
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `iia_Core/api_keys_template.py` to `iia_Core/api_keys.py`
   - Fill in your API keys in `api_keys.py`
   - Set up your database credentials in environment variables or settings.py

5. Set up the database:
```bash
python manage.py migrate
```

6. Run the development server:
```bash
python manage.py runserver
```

## Required API Keys

- Gemini API Key (for sentiment analysis)
- News API Key (for news integration)
- Google OAuth2 credentials (for authentication)
- Reddit API Key (for Reddit integration)

## Environment Variables

The following environment variables can be set:

- `DJANGO_SECRET_KEY`: Django secret key
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host
- `DB_PORT`: Database port

## License

This project is licensed under the MIT License - see the LICENSE file for details.
