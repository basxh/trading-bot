# 🤖 Modular Trading Bot

Ein modulärer Trading Bot in Python für Backtesting, Paper Trading und Live Trading.

## 📁 Projektstruktur

```
trading-bot/
├── trading_bot.py            # Haupt-Script mit CLI
├── config.json               # Konfigurationsdatei
├── data_fetcher.py           # Marktdaten-Modul
├── strategies.py             # Strategie-Modul
├── backtest.py               # Backtest-Modul
├── paper_trader.py           # Paper Trading Modul
├── live_trader.py            # Live Trading Vorbereitung
├── risk_management.py        # 🆕 Risk Management Module
├── optimizer.py              # 🆕 Parameter Optimierung
├── performance_analyzer.py   # 🆕 Performance Analytics
├── ml_trainer.py             # 🆕 ML Feature Engineering
├── rapid_backtest.py         # 🚀 Rapid Testing (5 Min)
├── strategy_comparison.py    # 🚀 Multi-Strategie Vergleich
├── walk_forward_test.py      # 🚀 Walk-Forward Analyse
├── rapid_test_suite.py       # 🚀 Kombinierte Test Suite
├── requirements.txt          # Python Abhängigkeiten
└── README.md                 # Diese Datei
```

## ✨ Features

### 📊 Marktdaten-Modul (`data_fetcher.py`)
- **Yahoo Finance** Integration für Aktien und ETFs
- **Binance API** Integration für Krypto
- Unterstützte Intervalle: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
- Daten-Export als CSV/JSON

### 🚀 Rapid Testing Framework (NEU!)

**Problem**: 10h Tests sind zu langsam für effiziente Entwicklung.

**Lösung**: Schnelles Testing in 20 Minuten statt 10 Stunden!

| Tool | Zeit | Zweck |
|------|------|-------|
| `rapid_backtest.py` | 5 Min | Einzelne Strategie testen |
| `strategy_comparison.py` | 15 Min | Multi-Strategie Vergleich |
| `walk_forward_test.py` | 20 Min | Robusteits-Analyse |
| `rapid_test_suite.py` | 20 Min | Komplette Pipeline |

**Score-System (0-100):**
- ⭐⭐⭐ **80-100**: Excellent - Paper Trading geeignet
- ⭐⭐ **60-79**: Good - Mit Vorsicht testen
- ⭐ **40-59**: OK - Weitere Optimierung nötig
- ❌ **0-39**: Poor - Nicht empfohlen

Siehe [Rapid Testing Guide](#-rapid-testing-guide) unten.

### 🧠 Strategie-Modul (`strategies.py`)
- Basis-Klasse für einfache Erweiterung
- **SMA Crossover**: Golden Cross / Death Cross Strategie
- **RSI**: Overbought/Oversold Strategie
- **MACD**: Moving Average Convergence Divergence Strategie
- **Bollinger**: Bollinger Bands Strategie
- **VWAP**: Volume Weighted Average Price Strategie
- **Combined**: Kombination aus SMA + RSI
- **Multi-Indicator**: Kombinierte Strategie mit mehreren Indikatoren
- **Mean Reversion**: Bounce-Strategie mit Bollinger + RSI
- **Momentum Breakout**: Trendfolge mit ATR
- **Range Scalper**: Range-Trading mit Support/Resistance
- Einfach erweiterbar für eigene Strategien

### 🛡️ Risk Management (`risk_management.py`)
- **ATR-basierte Positionssizing**: Volatilitätsabhängige Positionsgröße
- **Trailing Stop Loss**: Bewegt sich mit dem Gewinn
- **Kelly Criterion**: Optimale Positionsgröße basiernd auf Edge
- **Portfolio Risk Management**: Drawdown- und Daily Loss Limits
- **Stop Loss Management**: Automatisches Stop-Verlust-Tracking

### 📈 Performance Analytics (`performance_analyzer.py`)
- **Sharpe Ratio**: Risikoadjustierte Rendite
- **Sortino Ratio**: Nur Downside-Risiko
- **Calmar Ratio**: Rendite / Max Drawdown
- **Value at Risk (VaR)**: 95% und 99% Konfidenzniveau
- **Conditional VaR**: Expected Shortfall
- **Trade Statistics**: Gewinnrate, Profit Factor, Expectancy
- **Equity Curve Visualization**: Visualisierung mit matplotlib

### 🔧 Parameter Optimierung (`optimizer.py`)
- **Grid Search**: Testet verschiedene Parameter-Kombinationen
- **SMA Optimization**: Optimale SMA-Perioden finden
- **RSI Optimization**: Beste Overbought/Oversold Levels
- **Multi-Parameter**: Kombinierte Strategie-Optimierung
- **JSON Reports**: Speichert alle Testergebnisse

### 🤖 Machine Learning (`ml_trainer.py`)
- **Feature Engineering**: 50+ technische Indikatoren
- **Returns Features**: 1d, 5d, 10d, 20d Renditen
- **Volatility Features**: ATR, Standardabweichung
- **Target Creation**: Next-Day Return Klassifikation
- **CSV Export**: Trainingsdaten für externe ML-Modelle

### 📈 Backtest-Modul (`backtest.py`)
- Tests Strategien an historischen Daten
- Berechnet:
  - **Win Rate**: Prozentsatz gewinnender Trades
  - **Profit Factor**: Bruttogewinn / Bruttoverlust
  - **Max Drawdown**: Maximales Kapitalverhältnis
  - **Sharpe Ratio**: Risikoadjustierte Rendite
  - **Volatilität**: Jahresvolatilität
- Equity Curve Plotting
- JSON-Reports

### 💰 Paper Trading Modul (`paper_trader.py`)
- Simulierte Trades ohne echtes Geld
- Virtuelles Portfolio mit Startkapital
- SQLite Datenbank für Trade-History
- P&L Tracking (realisiert + unrealisiert)
- Portfoliobewertung in Echtzeit
- 🆕 Integriertes Risk Management (Stops, Position Sizing)

### 🔴 Live Trading Vorbereitung (`live_trader.py`)
- Gleiche Schnittstelle wie Paper Trader
- Broker Integration:
  - **Alpaca** (Aktien, ETFs)
  - **Binance** (Krypto)
- Safety Checks:
  - Max Position Size
  - Daily Loss Limit
  - Stop Loss
- Paper/Live Modus konfigurierbar
- 🆕 Integriertes Risk Management

### 🎛️ CLI Interface (`trading_bot.py`)
```bash
# Backtest durchführen
python trading_bot.py --mode backtest --symbol AAPL --strategy sma_crossover

# Paper Trading
python trading_bot.py --mode paper --symbol BTCUSDT --strategy rsi

# Mit Report und Plot
python trading_bot.py --mode backtest --symbol MSFT --strategy combined --save-report --plot

# Strategien auflisten
python trading_bot.py --list-strategies
```

## 🚀 Installation

### 1. Requirements installieren

```bash
cd trading-bot
pip install -r requirements.txt
```

### 2. Konfiguration anpassen

Die `config.json` Datei enthält alle Einstellungen:

```json
{
  "general": {
    "symbol": "AAPL",
    "market_type": "stock",
    "timezone": "America/New_York"
  },
  "data": {
    "interval": "1d",
    "period": "2y",
    "save_path": "data/"
  },
  "strategy": {
    "name": "sma_crossover",
    "params": {
      "sma_short": 50,
      "sma_long": 200,
      "rsi_period": 14,
      "rsi_overbought": 70,
      "rsi_oversold": 30
    }
  },
  "backtest": {
    "initial_capital": 10000,
    "commission": 0.001,
    "slippage": 0.0005
  },
  "paper_trading": {
    "initial_capital": 10000,
    "commission": 0.001,
    "check_interval": 60
  },
  "live_trading": {
    "enabled": false,
    "broker": "alpaca",
    "api_key": "",
    "api_secret": "",
    "paper": true,
    "max_position_size": 0.2,
    "max_daily_loss": 500,
    "stop_loss_pct": 0.02,
    "trailing_stop_pct": 0.03,
    "take_profit_pct": 0.05
  },
  "risk_management": {
    "use_risk_management": true,
    "max_position_pct": 0.2,
    "stop_loss_pct": 0.02,
    "trailing_stop_pct": 0.03,
    "take_profit_pct": 0.05,
    "max_daily_loss": 500,
    "max_drawdown_pct": 0.10,
    "kelly_fraction": 0.5
  },
  "logging": {
    "level": "INFO",
    "file": "logs/trading_bot.log"
  }
}
```

## 📖 Verwendung

### Backtest

```bash
python trading_bot.py --mode backtest --symbol AAPL --strategy sma_crossover
```

Output:
```
╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                            ║
╠══════════════════════════════════════════════════════════════╣
║  Initial Capital:    $10,000.00
║  Final Equity:       $12,456.32
║  Total Return:        +24.56%
╠══════════════════════════════════════════════════════════════╣
║  Total Trades:        23
║  Win Rate:            65.22%
║  Profit Factor:       2.34
║  Max Drawdown:        -8.45%
║  Sharpe Ratio:        1.56
║  Volatility (Ann.):   15.23%
╚══════════════════════════════════════════════════════════════╝
```

### Parameter Optimierung

```bash
# SMA Parameter optimieren
python optimizer.py --symbol AAPL --strategy sma_crossover --days 365 --metric sharpe_ratio

# RSI Parameter optimieren
python optimizer.py --symbol AAPL --strategy rsi --days 365 --metric profit_factor

# Ergebnisse werden in optimization_results/ gespeichert
```

### Performance Analytics

```bash
# Backtest-Results analysieren
python performance_analyzer.py --backtest-results results.json --save-report report.txt --save-plot equity.png
```

### ML Feature Engineering

```bash
# ML Trainingsdaten vorbereiten
python ml_trainer.py --symbol AAPL --days 365 --forecast-horizon 1

# Erzeugt:
# - ml_data/AAPL/train_1d_*.csv
# - ml_data/AAPL/test_1d_*.csv
# - ml_data/AAPL/features_1d_*.csv
```

### Paper Trading

```bash
python trading_bot.py --mode paper --symbol AAPL --strategy rsi
```

Zeigt das virtuelle Portfolio:
```
============================================================
📊 PAPER TRADING PORTFOLIO
============================================================
💰 Cash:           $5,432.10
📈 Total Value:    $10,876.54
💵 Initial:        $10,000.00
📊 Total P&L:      $+876.54 (+8.77%)
🔄 Trades:         12

📋 Positions:
  AAPL: 50.0000 @ $108.45 | Current: $109.00 | P&L: $+27.50
============================================================
```

### Live Trading ⚠️

**WARNUNG**: Erfordert API-Keys und führt echte Trades aus!

1. API Keys in `config.json` eintragen
2. Paper Mode testen: `"paper": true`
3. Dann auf Live umstellen: `"paper": false`

```bash
python trading_bot.py --mode live --symbol AAPL --strategy sma_crossover
```

## 🔧 Neue Strategie erstellen

1. In `strategies.py` eine neue Klasse erstellen:

```python
class My_Strategy(BaseStrategy):
    """Meine eigene Strategie."""
    
    def __init__(self, params=None):
        default_params = {'period': 20}
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        
        # Deine Indikator-Berechnungen hier
        df['my_indicator'] = df['close'].rolling(window=self.params['period']).mean()
        
        # Signale generieren
        df['signal'] = 0
        df.loc[df['close'] > df['my_indicator'], 'signal'] = 1
        df.loc[df['close'] < df['my_indicator'], 'signal'] = -1
        
        return df
```

2. Zur `STRATEGIES` Registry hinzufügen:

```python
STRATEGIES = {
    'sma_crossover': SMA_Crossover_Strategy,
    'rsi': RSI_Strategy,
    'macd': MACD_Strategy,
    'bollinger': Bollinger_Strategy,
    'vwap': VWAP_Strategy,
    'combined': Combined_Strategy,
    'multi_indicator': Multi_Indicator_Strategy,
    'mean_reversion': MeanReversionStrategy,
    'momentum_breakout': MomentumBreakoutStrategy,
    'range_scalper': RangeScalperStrategy,
    'my_strategy': My_Strategy  # Deine Strategie
}
```

3. Verwenden:

```bash
python trading_bot.py --mode backtest --strategy my_strategy
```

## 🔌 Broker API Setup

### Alpaca
1. Account erstellen: https://alpaca.markets
2. API Keys generieren
3. In `config.json` eintragen

### Binance
1. Account erstellen: https://binance.com
2. API Keys erstellen
3. In `config.json` eintragen
4. Testnet für Paper Trading nutzen

## 🛡️ Safety Features

- **Max Position Size**: Verhindert übermäßige Positionen
- **Daily Loss Limit**: Stoppt Trading nach Verlustlimit
- **Stop Loss**: Automatische Verkäufe bei Verlusten
- **Trailing Stop**: Bewegt sich mit Gewinn
- **Take Profit**: Automatische Gewinnmitnahme
- **Kelly Criterion**: Optimal Position Sizing
- **ATR Sizing**: Volatilitätsbasierte Größen
- **Paper Mode**: Testen ohne echtes Geld
- **Konfirmation**: Live Trading erfordert manuelle Bestätigung

## 📁 Erzeugte Dateien

```
data/
├── *.csv                        # Heruntergeladene Marktdaten
├── paper_trades_*.db            # SQLite Datenbank mit Trades

logs/
└── trading_bot.log              # Ausführliches Logging

reports/
└── *                            # Backtest Reports und Charts

optimization_results/
└── *.json                       # Optimierungsergebnisse

ml_data/
└── *                            # ML Trainingsdaten

rapid_test_results/
├── rapid_suite_*.json           # Komplette Pipeline-Ergebnisse
├── comparison_*.csv             # Strategie-Vergleich
└── comparison_*.json            # Rohdaten

rapid_results/
└── *.json                       # Einzelne Backtests

walk_forward_results/
└── *.json                       # Walk-Forward Ergebnisse
```

## 🧪 Testing

```bash
# Test mit verschiedenen Strategien
python trading_bot.py --mode backtest --symbol AAPL --strategy sma_crossover --save-report --plot
python trading_bot.py --mode backtest --symbol AAPL --strategy macd --save-report --plot
python trading_bot.py --mode backtest --symbol AAPL --strategy bollinger --save-report --plot
python trading_bot.py --mode backtest --symbol AAPL --strategy multi_indicator --save-report --plot

# Parameter Optimierung
python optimizer.py --symbol AAPL --strategy sma_crossover --days 365

# Performance Analyse
python performance_analyzer.py --backtest-results reports/AAPL_sma_crossover.json

# ML Data vorbereiten
python ml_trainer.py --symbol AAPL --days 365

# Crypto
python trading_bot.py --mode backtest --symbol BTC-USD --market-type crypto --strategy sma_crossover
```

---

# 🚀 Rapid Testing Guide

## Warum Rapid Testing?

**Vorher:** 10h parallele Paper Trading Tests für jede Strategie
**Jetzt:** 20 Minuten für komplette Validierung

## Die 4 Tools

### 1. rapid_backtest.py (5 Minuten)

Schneller Historischer Test auf 90 Tagen Daten:

```bash
# Einzelne Strategie testen
python rapid_backtest.py --strategy bollinger --symbol PLTR --days 90

# Mit Speichern und Plot
python rapid_backtest.py --strategy rsi --symbol AAPL --days 60 --save --plot

# Crypto
python rapid_backtest.py --strategy macd --symbol BTC-USD --market-type crypto
```

**Output:**
```
🚀 RAPID BACKTEST RESULTS
============================================================
Strategie:  bollinger
Symbol:     PLTR
Zeitraum:   90 Tage (2160 Datenpunkte)
------------------------------------------------------------
💰 Initial:        $10,000.00
💰 Final:          $11,245.30
📈 Total Return:   +12.45%
------------------------------------------------------------
🔄 Total Trades:   18
✅ Win Rate:       61.1%
📊 Profit Factor:  2.34
📉 Max Drawdown:   -8.45%
📊 Sharpe Ratio:   1.56
------------------------------------------------------------
🔄 Trades/Monat:   6.0
💵 Profit/Trade:   $69.18
🎯 Expectancy:     $42.15
------------------------------------------------------------
⭐ SCORE:          78.5/100
   Rating:         ⭐⭐ GOOD
============================================================
```

### 2. strategy_comparison.py (15 Minuten)

Vergleicht ALLE Strategien auf mehrere Assets:

```bash
# Alle Strategien auf Standard-Assets
python strategy_comparison.py --assets PLTR,ETH-USD,BTC-USD,TSLA --strategies all

# Nur spezifische Strategien
python strategy_comparison.py --assets AAPL,MSFT --strategies sma_crossover,rsi,bollinger

# Speichern der Ergebnisse
python strategy_comparison.py --assets PLTR --strategies all --save
```

**Output:**
```
🏆 STRATEGY COMPARISON RANKING
====================================================================================================

📊 Top 10 Strategie-Asset Kombinationen:
┌────┬──────────────────┬─────────┬────────┬───────────┬───────────────┬─────────┬────────┬──────────────┬─────────┬───────┐
│    │ Strategy         │ Asset   │ Trades │ Win Rate% │ Profit Factor │ Max DD% │ Sharpe │ Trades/Month │ Return% │ Score │
├────┼──────────────────┼─────────┼────────┼───────────┼───────────────┼─────────┼────────┼──────────────┼─────────┼───────┤
│  1 │ bollinger        │ PLTR    │     18 │      61.1 │          2.34 │   -8.45 │   1.56 │          6.0 │   12.45 │  78.5 │
│  2 │ sma_crossover    │ BTC-USD │     24 │      58.3 │          1.89 │  -12.30 │   1.23 │          8.0 │    8.92 │  72.3 │
└────┴──────────────────┴─────────┴────────┴───────────┴───────────────┴─────────┴────────┴──────────────┴─────────┴───────┘

🎯 TOP 3 EMPFEHLUNGEN:
   1. bollinger auf PLTR
      Score: 78.5 | Win Rate: 61.1% | PF: 2.34
```

### 3. walk_forward_test.py (20 Minuten)

Prüft Robustheit (kein Overfitting):

```bash
# Standard Walk-Forward (70% Train, 30% Test)
python walk_forward_test.py --strategy bollinger --symbol PLTR

# Mit Parameter-Optimierung auf Train
python walk_forward_test.py --strategy sma_crossover --symbol AAPL --optimize-params

# Mehr Test-Daten
python walk_forward_test.py --strategy rsi --symbol BTC-USD --days 60 --train-ratio 0.6
```

**Output:**
```
🔄 WALK-FORWARD TEST RESULTS
======================================================================
Strategie: bollinger | Symbol: PLTR
Train/Test Split: 70%/30%
----------------------------------------------------------------------

📊 TRAIN SET ERGEBNISSE:
   Trades:         14
   Return:         +15.23%
   Win Rate:       64.3%
   Profit Factor:  2.56
   Max Drawdown:   -6.80%

📊 TEST SET ERGEBNISSE (Ungesehene Daten):
   Trades:         4
   Return:         +3.12%
   Win Rate:       50.0%
   Profit Factor:  1.45
   Max Drawdown:   -4.20%

----------------------------------------------------------------------
🔍 ROBUSTHEIT ANALYSE:
   Return Diff:    -12.11%
   Win Rate Diff:  -14.3%
   PF Diff:        -1.11
----------------------------------------------------------------------
   Robustness Score: 72/100
   Verdict:          ✅ ROBUST - Kein Overfitting erkannt
   Empfehlung:       Geeignet für Paper Trading
======================================================================
```

### 4. rapid_test_suite.py (20 Minuten)

Komplette Pipeline in einem Command:

```bash
# Quick Test (5 Min)
python rapid_test_suite.py --symbol PLTR --quick-test --strategy bollinger

# Full Pipeline (20 Min) - Testet alle Strategien + Walk-Forward
python rapid_test_suite.py --symbol PLTR --full-test

# Crypto
python rapid_test_suite.py --symbol BTC-USD --market-type crypto --full-test

# Zeige alle Beispiele
python rapid_test_suite.py --examples
```

**Output (Full Pipeline):**
```
======================================================================
🚀 RAPID TEST SUITE - Full Pipeline
======================================================================
Asset: PLTR | Markt: stock | Zeitraum: 90 Tage

======================================================================
📊 PHASE 1: Multi-Strategie Vergleich
======================================================================
[... Tabelle mit allen Strategien ...]

======================================================================
🔄 PHASE 2: Walk-Forward Analyse (Top Strategy)
   Strategie: bollinger
======================================================================
[... Walk-Forward Ergebnisse ...]

======================================================================
🎯 PHASE 3: Final Recommendation
======================================================================

   Beste Strategie:   bollinger auf PLTR
   Overall Score:     75.2/100
   Backtest Score:    78.5/100
   Robustness Score:  72/100
   Risk Level:        MEDIUM
----------------------------------------------------------------------
   DECISION:          ✅ GO
   Confidence:        HIGH
   Action:            Start Paper Trading
======================================================================
```

## Workflow: Von 10h zu 20 Minuten

### Vorher (Langsam):
```
1. Strategie implementieren
2. 3 parallele Paper Trading Tests (je 6h) = 18h
3. Ergebnisse analysieren
4. Parameter anpassen
5. Wiederholen...
```

### Jetzt (Schnell):
```
1. Strategie implementieren
2. Rapid Backtest (5 Min)
   └─ Score < 50? → Strategie verbessern → 2.
   └─ Score >= 50? → Weiter zu 3.
3. Strategy Comparison auf mehrere Assets (15 Min)
   └─ Top 3 identifizieren
4. Walk-Forward für beste Kombination (20 Min)
   └─ Robustheit prüfen
5. Entscheidung:
   └─ Score >= 75? → Paper Trading starten
   └─ Score 60-75? → Kurzer Paper Test
   └─ Score < 60? → Strategie ablehnen

Gesamt: 20-40 Minuten statt 10+ Stunden!
```

## Empfohlener Workflow

### Für Neue Strategien:
```bash
# 1. Schneller Check (5 Min)
python rapid_backtest.py --strategy meine_strategie --symbol PLTR

# 2. Falls Score > 50: Auf mehrere Assets testen (15 Min)
python strategy_comparison.py --assets PLTR,AAPL,BTC-USD --strategies meine_strategie

# 3. Falls gut: Walk-Forward für Robustheit (20 Min)
python walk_forward_test.py --strategy meine_strategie --symbol PLTR --optimize-params
```

### Für Strategie-Entwicklung:
```bash
# Volle Pipeline direkt
python rapid_test_suite.py --symbol PLTR --full-test

# Ergebnis zeigt sofort ob Strategie Paper-Trading-tauglich ist!
```

## Score-System

| Score | Rating | Bedeutung |
|-------|--------|-----------|
| 80-100 | ⭐⭐⭐ EXCELLENT | Paper Trading geeignet |
| 60-79 | ⭐⭐ GOOD | Mit Vorsicht testen |
| 40-59 | ⭐ OK | Weitere Optimierung nötig |
| 0-39 | ❌ POOR | Nicht empfohlen |

**Berechnung:**
- Win Rate (30%): Höher ist besser, max 70%
- Profit Factor (25%): Bruttogewinn / Bruttoverlust, max 3.0
- Trades/Monat (15%): Aktivität, max 20
- Sharpe Ratio (20%): Risikoadjustierte Rendite, max 3.0
- Max Drawdown (10%): Kleiner ist besser, max -20%

## Erzeugte Dateien

```
rapid_test_results/
├── rapid_suite_PLTR_20240419_143022.json      # Komplette Pipeline
├── comparison_20240419_143022.csv             # Strategie-Vergleich
└── comparison_20240419_143022.json            # Rohdaten

rapid_results/
└── bollinger_PLTR_20240419_142500.json         # Einzelne Backtests

walk_forward_results/
└── bollinger_PLTR_20240419_143000.json         # Walk-Forward Ergebnisse
```

## 📚 Weiterführende Links

- [yfinance Dokumentation](https://github.com/ranaroussi/yfinance)
- [Alpaca API](https://alpaca.markets/docs/)
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)

## ⚠️ Disclaimer

**Dieser Bot ist für Bildungszwecke gedacht. Verwenden Sie Live Trading auf eigene Gefahr. Vergangene Performance ist keine Garantie für zukünftige Ergebnisse.**
