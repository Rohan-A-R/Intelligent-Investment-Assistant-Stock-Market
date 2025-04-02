from django.shortcuts import render
from django.http import HttpResponse
import yfinance as yf
from .models import StockPrice
from .fenwick import FenwickTree
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

    return render(request, 'stocks/stock_dashboard.html', {
        'stock_prices': stock_prices[:10],  # Last 10 for table
        'chart_data': json.dumps(chart_data),
        'range_sum': range_sum,
        'range_left': 2,
        'range_right': 5,
        'predicted_price': next_price,
        'symbol': symbol,
    })