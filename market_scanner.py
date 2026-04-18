#!/usr/bin/env python3
"""
Market Scanner - Analyzes assets for trading opportunities
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

# Asset lists
TECH_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
CRYPTO = ['BTC-USD', 'ETH-USD']
ETFS = ['SPY', 'QQQ', 'IWM']
VOLATILE = ['GME', 'AMC', 'PLTR']

ALL_ASSETS = TECH_STOCKS + CRYPTO + ETFS + VOLATILE

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_adx(df, period=14):
    """Calculate ADX (Average Directional Index)"""
    plus_dm = df['High'].diff()
    minus_dm = df['Low'].diff().abs()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr = calculate_atr(df, period)
    
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * plus_dm.rolling(window=period).mean() / atr
    minus_di = 100 * minus_dm.rolling(window=period).mean() / atr
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx.iloc[-1] if len(adx) > 0 else 0

def count_swing_points(df, window=5):
    """Count swing highs and lows"""
    highs = df['High']
    lows = df['Low']
    
    swing_highs = 0
    swing_lows = 0
    
    for i in range(window, len(highs) - window):
        # Swing high
        if highs.iloc[i] == highs.iloc[i-window:i+window+1].max():
            swing_highs += 1
        # Swing low
        if lows.iloc[i] == lows.iloc[i-window:i+window+1].min():
            swing_lows += 1
    
    return swing_highs + swing_lows

def analyze_asset(symbol):
    """Analyze a single asset"""
    try:
        # Download 60 days to have enough data for 30-day calculations
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d")
        
        if len(df) < 30:
            return None
        
        # Use last 30 days
        df = df.tail(30)
        
        # Calculate daily returns
        df['Returns'] = df['Close'].pct_change().dropna()
        
        # Annualized volatility (252 trading days)
        volatility = df['Returns'].std() * np.sqrt(252) * 100
        
        # Average daily range (High - Low)
        daily_range = (df['High'] - df['Low']).mean()
        avg_price = df['Close'].mean()
        avg_range_pct = (daily_range / avg_price) * 100
        
        # ADX for trend strength
        adx = calculate_adx(df)
        
        # Trend direction
        sma_10 = df['Close'].rolling(window=10).mean().iloc[-1]
        sma_20 = df['Close'].rolling(window=20).mean().iloc[-1]
        current_price = df['Close'].iloc[-1]
        
        if current_price > sma_10 > sma_20:
            trend = "up"
        elif current_price < sma_10 < sma_20:
            trend = "down"
        else:
            trend = "sideways"
        
        # Swing opportunities
        swings = count_swing_points(df)
        
        # Volume (average)
        avg_volume = df['Volume'].mean()
        
        return {
            "symbol": symbol,
            "volatility": round(volatility, 2),
            "atr": round(avg_range_pct, 2),
            "trend": trend,
            "adx": round(adx, 2),
            "swings": swings,
            "avg_volume": int(avg_volume),
            "current_price": round(current_price, 2),
            "price_change_30d": round((current_price / df['Close'].iloc[0] - 1) * 100, 2)
        }
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def main():
    print("=" * 60)
    print("MARKET SCANNER - Trading Opportunities")
    print("=" * 60)
    
    results = []
    failed = []
    
    for i, symbol in enumerate(ALL_ASSETS, 1):
        print(f"\n[{i}/{len(ALL_ASSETS)}] Analyzing {symbol}...")
        data = analyze_asset(symbol)
        if data:
            results.append(data)
            print(f"  ✓ Volatility: {data['volatility']:.1f}% | Trend: {data['trend']} | Swings: {data['swings']}")
        else:
            failed.append(symbol)
            print(f"  ✗ Failed to analyze")
    
    print("\n" + "=" * 60)
    print("SCAN COMPLETE - Processing Results")
    print("=" * 60)
    
    # Filter for high volatility (>30%)
    high_vol = [r for r in results if r['volatility'] > 30]
    
    # Sort by multiple factors: volatility, swings, volume
    def score(r):
        vol_score = min(r['volatility'] / 100, 1.0) * 40  # Max 40 points
        swing_score = min(r['swings'] / 5, 1.0) * 30  # Max 30 points
        volume_score = min(np.log10(r['avg_volume']) / 10, 1.0) * 30  # Max 30 points
        return vol_score + swing_score + volume_score
    
    for r in results:
        r['score'] = round(score(r), 2)
    
    # Sort by score
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    # Top 5 recommendations
    top_5 = sorted_results[:5]
    
    # Assets to avoid (low volatility, no clear trend, or very low volume)
    avoid = [r['symbol'] for r in results if r['volatility'] < 15 and r['adx'] < 20]
    
    # Build output
    output = {
        "top_markets": [
            {
                "symbol": r['symbol'],
                "volatility": r['volatility'],
                "atr": r['atr'],
                "trend": r['trend'],
                "adx": r['adx'],
                "swings": r['swings'],
                "score": r['score'],
                "current_price": r['current_price'],
                "price_change_30d": r['price_change_30d']
            }
            for r in top_5
        ],
        "avoid": avoid,
        "all_assets": sorted_results,
        "timestamp": datetime.now().isoformat(),
        "scan_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    # Save to file
    output_path = "/data/.openclaw/workspace/projects/trading-bot/data/market_scan_2026-04-19.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("TOP 5 RECOMMENDATIONS")
    print("=" * 60)
    for i, r in enumerate(top_5, 1):
        trend_icon = {"up": "📈", "down": "📉", "sideways": "↔️"}[r['trend']]
        print(f"{i}. {r['symbol']:6} | Vol: {r['volatility']:5.1f}% | ATR: {r['atr']:4.1f}% | {trend_icon} {r['trend']:8} | Score: {r['score']:.1f}")
    
    print("\n" + "=" * 60)
    print("AVOID (Low Volatility / No Trend)")
    print("=" * 60)
    print(", ".join(avoid) if avoid else "None")
    
    if failed:
        print("\n⚠ Failed to analyze:", ", ".join(failed))
    
    return output

if __name__ == "__main__":
    main()
