from django.shortcuts import render, redirect
from django.http import HttpResponse
import yfinance as yf
from .models import StockPrice, Portfolio
from .fenwick import FenwickTree
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import json
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split

def fetch_stock_data(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="5d", interval="1h")  # 5 days, 1-hour intervals
    for index, row in data.iterrows():
        StockPrice.objects.update_or_create(
            symbol=symbol.upper(),
            timestamp=index,
            defaults={
                'open_price': row['Open'],
                'high_price': row['High'],
                'low_price': row['Low'],
                'close_price': row['Close'],
                'volume': int(row['Volume']),
            }
        )

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('stock_dashboard')
            else:
                return HttpResponse("Authentication failed after registration.", status=400)
    else:
        form = UserCreationForm()
    return render(request, 'stocks/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('stock_dashboard')
            else:
                return render(request, 'stocks/login.html', {
                    'form': form,
                    'error': 'Invalid username or password'
                })
    else:
        form = AuthenticationForm()
    return render(request, 'stocks/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('stock_dashboard')

@login_required
def portfolio(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol', '').upper()
        try:
            purchase_price = float(request.POST.get('purchase_price', 0))
            quantity = int(request.POST.get('quantity', 0))
            if symbol and purchase_price > 0 and quantity > 0:
                Portfolio.objects.create(
                    user=request.user,
                    symbol=symbol,
                    purchase_price=purchase_price,
                    quantity=quantity
                )
                messages.success(request, f"{symbol} added to your portfolio!")
            else:
                messages.error(request, "Invalid input. Ensure all fields are valid.")
        except ValueError:
            messages.error(request, "Invalid price or quantity. Please enter numbers.")
        return redirect('portfolio')

    portfolio_items = Portfolio.objects.filter(user=request.user)
    current_prices = {}
    total_gains = 0
    prices_list = []
    gains = {}

    for item in portfolio_items:
        latest_price = StockPrice.objects.filter(symbol=item.symbol).order_by('-timestamp').first()
        if latest_price:
            current_prices[item.symbol] = latest_price.close_price
            gain = (latest_price.close_price - item.purchase_price) * item.quantity
            gains[item.symbol] = gain
            total_gains += gain
            prices_list.append(gain)

    # Fenwick Tree for cumulative gains
    fenwick = FenwickTree(len(prices_list))
    for i, gain in enumerate(prices_list):
        fenwick.update(i, gain)
    cumulative_gains = fenwick.query(len(prices_list) - 1) if prices_list else 0

    return render(request, 'stocks/portfolio.html', {
        'portfolio_items': portfolio_items,
        'current_prices': current_prices,
        'gains': gains,
        'total_gains': total_gains,
        'cumulative_gains': cumulative_gains,
    })

def stock_dashboard(request):
    symbol = request.GET.get('symbol', 'AAPL').upper()  # Default to AAPL
    if request.method == 'GET' and 'symbol' in request.GET:
        fetch_stock_data(symbol)  # Fetch and store data when a new symbol is searched

    # Fetch last 50 hourly entries
    stock_prices = StockPrice.objects.filter(symbol=symbol).order_by('-timestamp')[:50]
    if not stock_prices.exists():
        fetch_stock_data(symbol)  # Fetch if no data exists
        stock_prices = StockPrice.objects.filter(symbol=symbol).order_by('-timestamp')[:50]

    prices = [float(price.close_price) for price in stock_prices[::-1]]  # Chronological order

    # Fenwick Tree
    fenwick = FenwickTree(len(prices))
    for i, price in enumerate(prices):
        fenwick.update(i, price)
    range_sum = fenwick.range_query(2, 5)

    # Prepare data for XGBoost
    df = pd.DataFrame({
        'close': prices,
        'volume': [price.volume for price in stock_prices[::-1]],
    })
    for lag in range(1, 4):
        df[f'close_lag_{lag}'] = df['close'].shift(lag)
    df = df.dropna()

    X = df[['close_lag_1', 'close_lag_2', 'close_lag_3', 'volume']]
    y = df['close']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # Train XGBoost
    model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=3)
    model.fit(X_train, y_train)
    last_data = X.iloc[-1:].values
    next_price = model.predict(last_data)[0]

    # Chart data (last 10 for display)
    labels = [price.timestamp.strftime('%Y-%m-%d %H:%M') for price in stock_prices[::-1]][-10:]
    chart_prices = prices[-10:]
    chart_data = {'labels': labels, 'data': chart_prices}

    # Fetch news for the stock
    stock = yf.Ticker(symbol)
    news = stock.news if hasattr(stock, 'news') else []

    # Process news to extract title and link from nested content
    news_items = []
    for item in news[:5]:
        content = item.get('content', {})
        title = content.get('title', 'No title')
        # Safely extract the link from clickThroughUrl or canonicalUrl
        click_url = content.get('clickThroughUrl')
        canonical_url = content.get('canonicalUrl')
        link = '#'
        if isinstance(click_url, dict):
            link = click_url.get('url', '#')
        elif isinstance(canonical_url, dict):
            link = canonical_url.get('url', '#')
        
        # Only add news items with valid titles and links
        if title != 'No title' and link != '#':
            news_items.append({'title': title, 'link': link})


    context = {
        'stock_prices': stock_prices[:10],
        'chart_data': json.dumps(chart_data),
        'range_sum': range_sum,
        'range_left': 2,
        'range_right': 5,
        'predicted_price': next_price,
        'symbol': symbol,
        'news_items': news_items,
    }
    if request.user.is_authenticated:
        context['can_add_to_portfolio'] = True
    return render(request, 'stocks/stock_dashboard.html', context)