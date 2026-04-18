# Reactive Trading Strategies - Backtest Results

**Datum:** 2026-04-19

## Entwickelte Strategien

### 1. Mean Reversion (Bounce) Strategy
- **Konzept:** Kaufe wenn Preis unter untere Bollinger Band fällt, verkaufe bei Rückkehr zur Mitte
- **Indikatoren:** Bollinger Bands (20, 2.0), RSI (14)
- **Entry:** Close < Lower Band AND RSI < 40
- **Exit:** Close > Middle Band OR Stop Loss 3%
- **Timeframe:** 1h empfohlen

### 2. Momentum Breakout Strategy  
- **Konzept:** Folge starken Trends wenn Volatilität explodiert
- **Indikatoren:** ATR (14), SMA (20)
- **Entry:** Close > SMA + 1.5xATR (Long) / Close < SMA - 1.5xATR (Short)
- **Exit:** ATR Trailing Stop
- **Timeframe:** 15min oder 1h

### 3. Range Scalping Strategy
- **Konzept:** Trade innerhalb einer Range (Support/Resistance)
- **Indikatoren:** Rolling Support/Resistance (20), RSI (14)
- **Entry:** Near Support + RSI < 30 (Long) / Near Resistance + RSI > 70 (Short)
- **Exit:** Gegenseite der Range
- **Timeframe:** 15min

---

## Backtest Ergebnisse (TSLA & BTC, letzte 30 Tage)

| Strategy | Symbol | Timeframe | Trades | Win_Rate | Profit_Factor | Return_Pct | Max_DD | Sharpe |
|----------|--------|-----------|--------|----------|---------------|------------|--------|--------|
| Mean_Reversion | TSLA | 1h | 3 | 33.3% | 0.06 | -6.63% | -9.85% | -1.33 |
| Momentum_Breakout | TSLA | 1h | 4 | 0.0% | 0.00 | +6.80% | -7.46% | 0.75 |
| Range_Scalper | TSLA | 1h | 3 | 0.0% | 0.00 | -6.67% | -11.61% | -0.70 |
| Mean_Reversion | TSLA | 15m | 17 | 41.2% | 0.49 | -8.30% | -11.47% | -0.57 |
| Momentum_Breakout | TSLA | 15m | 22 | 31.8% | 0.65 | -8.16% | -19.34% | -0.47 |
| Range_Scalper | TSLA | 15m | 13 | 61.5% | 0.81 | -3.79% | -17.11% | -0.20 |
| Mean_Reversion | BTCUSDT | 1h | 11 | 54.5% | 0.39 | -5.91% | -7.36% | -0.73 |
| Momentum_Breakout | BTCUSDT | 1h | 15 | 53.3% | 1.47 | +4.07% | -6.12% | 0.30 |
| Range_Scalper | BTCUSDT | 1h | 12 | 66.7% | 1.16 | +0.24% | -7.40% | 0.04 |
| Mean_Reversion | BTCUSDT | 15m | 13 | 23.1% | 0.19 | -4.33% | -4.50% | -0.97 |
| Momentum_Breakout | BTCUSDT | 15m | 18 | 27.8% | 0.71 | -2.63% | -6.63% | -0.33 |
| Range_Scalper | BTCUSDT | 15m | 20 | 40.0% | 0.28 | -4.97% | -5.02% | -0.86 |

---

## Trades pro Tag

| Strategy | Symbol | Timeframe | Trades/Tag |
|----------|--------|-----------|------------|
| Mean_Reversion | TSLA | 1h | 0.1 |
| Momentum_Breakout | TSLA | 1h | 0.1 |
| Range_Scalper | TSLA | 1h | 0.1 |
| Mean_Reversion | TSLA | 15m | 0.6 |
| **Momentum_Breakout** | **TSLA** | **15m** | **0.7** |
| Range_Scalper | TSLA | 15m | 0.4 |
| Mean_Reversion | BTCUSDT | 1h | 0.4 |
| Momentum_Breakout | BTCUSDT | 1h | 0.5 |
| Range_Scalper | BTCUSDT | 1h | 0.4 |
| Mean_Reversion | BTCUSDT | 15m | 0.4 |
| Momentum_Breakout | BTCUSDT | 15m | 0.6 |
| Range_Scalper | BTCUSDT | 15m | 0.7 |

---

## Beste Performer

1. **Momentum_Breakout (TSLA 1h):** +6.80% Return
2. **Momentum_Breakout (BTCUSDT 1h):** +4.07% Return  
3. **Range_Scalper (BTCUSDT 1h):** +0.24% Return

---

## Erkenntnisse & Nächste Schritte

### Aktueller Status
- **Problem:** SMA Crossover war zu langsam (0 Trades in 16 Minuten)
- **Ergebnis:** Neue Strategien generieren 0.1-0.7 Trades/Tag
- **Ziel:** 10-50 Trades/Tag - NOCH NICHT ERREICHT

### Empfohlene Optimierungen
1. **Kürzere Timeframes:** 5min oder 1min statt 15min
2. **Aggressivere Entry-Conditions:** Weniger Filter, mehr Signale
3. **Pyramiding:** Mehrere Positionen pro Tag erlauben
4. **Multi-Symbol Trading:** Mehrere Assets gleichzeitig traden
5. **Parameter-Tuning:** Mit optimizer.py die besten Parameter finden

### Verwendung
```python
from strategies import get_strategy, STRATEGIES

# Neue Strategien verfügbar:
strategy = get_strategy('mean_reversion')
strategy = get_strategy('momentum_breakout')  
strategy = get_strategy('range_scalper')
```

---

## Files
- `strategies.py` - Enthält alle 3 neuen Strategien
- `test_reactive_strategies.py` - Backtest Script

## Strategie-Registry
```python
STRATEGIES = {
    'sma_crossover': SMA_Crossover_Strategy,
    'rsi': RSI_Strategy,
    'combined': Combined_Strategy,
    'macd': MACD_Strategy,
    'bollinger': Bollinger_Strategy,
    'vwap': VWAP_Strategy,
    'multi_indicator': Multi_Indicator_Strategy,
    'mean_reversion': MeanReversionStrategy,      # NEU
    'momentum_breakout': MomentumBreakoutStrategy,  # NEU
    'range_scalper': RangeScalperStrategy,          # NEU
}
```
