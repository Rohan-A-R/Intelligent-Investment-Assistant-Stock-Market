import yfinance as yf
import requests
import json
import praw
from django.shortcuts import render
from .models import SentimentAnalysis
from google import generativeai as genai
from google.generativeai import types
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from django.core.cache import cache

from iia_Core.settings import GEMINI_API_KEY, NEWS_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

def fetch_stock_data(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info
    stock_details = {
        'name': info.get('longName', 'N/A'),
        'current_price': info.get('regularMarketPrice', info.get('currentPrice', 0)),
        'market_cap': info.get('marketCap', 'N/A'),
        'pe_ratio': info.get('trailingPE', 'N/A'),
        'dividend_yield': info.get('dividendYield', 'N/A'),
        'revenue': info.get('totalRevenue', 'N/A'),
        'net_income': info.get('netIncomeToCommon', 'N/A'),
    }
    return stock_details

def fetch_news(symbol):
    cache_key = f"news_{symbol}"
    cached_news = cache.get(cache_key)
    if cached_news:
        return cached_news

    try:
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        news = newsapi.get_everything(
            q=symbol,
            from_param=from_date,
            to=to_date,
            language='en',
            sort_by='relevancy',
            page_size=5
        )
        news_items = []
        for article in news.get('articles', []):
            if article.get('title') and article.get('url'):
                news_items.append({
                    'title': article.get('title'),
                    'link': article.get('url'),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'published_at': article.get('publishedAt'),
                    'description': article.get('description', '')
                })
        
        cache.set(cache_key, news_items, timeout=3600)  # Cache for 1 hour
        return news_items
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def fetch_reddit_data(symbol):
    cache_key = f"reddit_{symbol}"
    cached_reddit_data = cache.get(cache_key)
    if cached_reddit_data:
        return cached_reddit_data

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
        analyzer = SentimentIntensityAnalyzer()

        subreddits = ['stocks', 'wallstreetbets', 'investing']
        reddit_posts = []

        for subreddit_name in subreddits:
            subreddit = reddit.subreddit(subreddit_name)
            for submission in subreddit.search(symbol, limit=3):
                title = submission.title or ""
                selftext = submission.selftext or ""
                combined_text = f"{title} {selftext}".strip()
                sentiment_score = analyzer.polarity_scores(combined_text)['compound']

                sentiment_label = (
                    'positive' if sentiment_score > 0.05 else
                    'negative' if sentiment_score < -0.05 else
                    'neutral'
                )

                reddit_posts.append({
                    'title': title,
                    'url': submission.url,
                    'selftext': selftext,
                    'subreddit': subreddit_name,
                    'sentiment': sentiment_label,
                    'sentiment_score': round(sentiment_score, 3)
                })

        cache.set(cache_key, reddit_posts, timeout=3600)  # Cache for 1 hour
        return reddit_posts
    except Exception as e:
        print(f"Error fetching Reddit data: {e}")
        return []


def get_gemini_sentiment(stock_details, news_items, reddit_posts):
    client = genai.GenerativeModel('gemini-2.0-flash')
    genai.configure(api_key=GEMINI_API_KEY)
    formatted_news = []
    for item in news_items:
        formatted_news.append({
            'title': item['title'],
            'source': item['source'],
            'description': item['description'],
            'published_at': item['published_at']
        })

    formatted_reddit = []
    for post in reddit_posts:
        formatted_reddit.append({
            'title': post['title'],
            'subreddit': post['subreddit'],
            'text': post['selftext']
        })

    prompt = f"""
    Analyze the following stock data, news, and Reddit posts for the stock symbol provided.
    Stock Fundamentals: {json.dumps(stock_details)}
    News: {json.dumps(formatted_news)}
    Reddit Posts: {json.dumps(formatted_reddit)}

    Provide a structured response with:
    1. A summary of the stock (2-3 sentences describing its current state).
    2. 3-4 key points summarizing the news (bullet points).
    3. 3-4 key points summarizing the Reddit posts (bullet points).
    4. Sentiment analysis for:
       - Stock fundamentals (positive, negative, neutral).
       - News (positive, negative, neutral).
       - Reddit (positive, negative, neutral).
    5. An overall sentiment (positive, negative, neutral).
    6. A stock recommendation (Buy, Sell, Hold).
    7. A predicted stock price based on the sentiment and data.
    """

    try:
        response = client.generate_content(
            contents=[prompt],
            generation_config=types.GenerationConfig(
                max_output_tokens=1000,
                temperature=0.7
            )
        )
        raw_summary = response.text

        summary = "No summary available."
        news_points = []
        reddit_points = []
        sentiment_fundamentals = "neutral"
        sentiment_news = "neutral"
        sentiment_reddit = "neutral"
        overall_sentiment = "neutral"
        recommendation = "Hold"
        predicted_price = stock_details['current_price']

        if "Stock Summary:" in raw_summary:
            summary = raw_summary.split("Stock Summary:")[1].split("News Points:")[0].strip()
        if "News Points:" in raw_summary:
            news_section = raw_summary.split("News Points:")[1].split("Reddit Points:")[0].strip()
            news_points = [point.strip() for point in news_section.split("\n") if point.strip().startswith("-")][:4]
        if "Reddit Points:" in raw_summary:
            reddit_section = raw_summary.split("Reddit Points:")[1].split("Sentiment Analysis:")[0].strip()
            reddit_points = [point.strip() for point in reddit_section.split("\n") if point.strip().startswith("-")][:4]
        if "Sentiment Analysis:" in raw_summary:
            sentiment_section = raw_summary.split("Sentiment Analysis:")[1].split("Overall Sentiment:")[0].strip()
            if "Fundamentals:" in sentiment_section:
                sentiment_fundamentals = sentiment_section.split("Fundamentals:")[1].split("\n")[0].strip().lower()
            if "News:" in sentiment_section:
                sentiment_news = sentiment_section.split("News:")[1].split("\n")[0].strip().lower()
            if "Reddit:" in sentiment_section:
                sentiment_reddit = sentiment_section.split("Reddit:")[1].split("\n")[0].strip().lower()
        if "Overall Sentiment:" in raw_summary:
            overall_sentiment = raw_summary.split("Overall Sentiment:")[1].split("Recommendation:")[0].strip().lower()
        if "Recommendation:" in raw_summary:
            recommendation = raw_summary.split("Recommendation:")[1].split("Predicted Price:")[0].strip()
        if "Predicted Price:" in raw_summary:
            try:
                predicted_price = float(raw_summary.split("Predicted Price:")[1].strip())
            except (IndexError, ValueError):
                pass

        return {
            'summary': summary,
            'news_points': news_points,
            'reddit_points': reddit_points,
            'sentiment_fundamentals': sentiment_fundamentals,
            'sentiment_news': sentiment_news,
            'sentiment_reddit': sentiment_reddit,
            'overall_sentiment': overall_sentiment,
            'recommendation': recommendation,
            'predicted_price': predicted_price
        }
    except Exception as e:
        print(f"Error with Gemini API: {e}")
        return {
            'summary': 'Error in Gemini API',
            'news_points': [],
            'reddit_points': [],
            'sentiment_fundamentals': 'neutral',
            'sentiment_news': 'neutral',
            'sentiment_reddit': 'neutral',
            'overall_sentiment': 'neutral',
            'recommendation': 'Hold',
            'predicted_price': stock_details['current_price']
        }

def sentiment_dashboard(request):
    symbol = request.GET.get('symbol', 'AAPL').upper()
    stock_details = fetch_stock_data(symbol)
    news_items = fetch_news(symbol)
    reddit_posts = fetch_reddit_data(symbol)

    sentiment_data = get_gemini_sentiment(stock_details, news_items, reddit_posts)

    SentimentAnalysis.objects.create(
        symbol=symbol,
        summary=sentiment_data['summary'],
        recommendation=sentiment_data['recommendation'],
        predicted_price=sentiment_data['predicted_price']
    )

    recent_analyses = SentimentAnalysis.objects.filter(symbol=symbol).order_by('-analysis_date')[:5]

    context = {
        'symbol': symbol,
        'stock_details': stock_details,
        'news_items': news_items,
        'reddit_posts': reddit_posts,
        'sentiment_data': sentiment_data,
        'recent_analyses': recent_analyses,
    }
    return render(request, 'stocks/sentiment.html', context)

def some_view(request):
    # Your view logic here
    pass
