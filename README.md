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
├── requirements.txt          # Python Abhängigkeiten
└── README.md                 # Diese Datei
```

## ✨ Features

### 📊 Marktdaten-Modul (`data_fetcher.py`)
- **Yahoo Finance** Integration für Aktien und ETFs
- **Binance API** Integration für Krypto
- Unterstützte Intervalle: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
- Daten-Export als CSV/JSON

### 🧠 Strategie-Modul (`strategies.py`)
- Basis-Klasse für einfache Erweiterung
- **SMA Crossover**: Golden Cross / Death Cross Strategie
- **RSI**: Overbought/Oversold Strategie
- **MACD**: Moving Average Convergence Divergence Strategie
- **Bollinger**: Bollinger Bands Strategie
- **VWAP**: Volume Weighted Average Price Strategie
- **Combined**: Kombination aus SMA + RSI
- **Multi-Indicator**: Kombinierte Strategie mit mehreren Indikatoren
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
    "symbol": "AAPL",           // Trading Symbol
    "market_type": "stock",     // "stock" oder "crypto"
    "timezone": "America/New_York"
  },
  "data": {
    "interval": "1d",           // 1m, 5m, 1h, 1d
    "period": "2y",             // Lookback Periode
    "save_path": "data/"
  },
  "strategy": {
    "name": "sma_crossover",    // siehe strategies.py
    "params": {
      "sma_short": 50,          // Kurzfristige SMA
      "sma_long": 200,          // Langfristige SMA
      "rsi_period": 14,
      "rsi_overbought": 70,
      "rsi_oversold": 30
    }
  },
  "backtest": {
    "initial_capital": 10000,
    "commission": 0.001,        // 0.1% Gebühr
    "slippage": 0.0005          // 0.05% Slippage
  },
  "paper_trading": {
    "initial_capital": 10000,
    "commission": 0.001,
    "check_interval": 60
  },
  "live_trading": {
    "enabled": false,
    "broker": "alpaca",         // "alpaca" oder "binance"
    "api_key": "",
    "api_secret": "",
    "paper": true,              // true = Paper, false = Live
    "max_position_size": 0.2,   // Max 20% des Portfolios
    "max_daily_loss": 500,      // Max $500 Verlust/Tag
    "stop_loss_pct": 0.02,      // 2% Stop Loss
    "trailing_stop_pct": 0.03,  // 3% Trailing Stop
    "take_profit_pct": 0.05     // 5% Take Profit
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

- `data/*.csv` - Heruntergeladene Marktdaten
- `data/paper_trades_*.db` - SQLite Datenbank mit Trades
- `logs/trading_bot.log` - Ausführliches Logging
- `reports/*` - Backtest Reports und Charts
- `optimization_results/*.json` - Optimierungsergebnisse
- `ml_data/*` - ML Trainingsdaten

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

## 📚 Weiterführende Links

- [yfinance Dokumentation](https://github.com/ranaroussi/yfinance)
- [Alpaca API](https://alpaca.markets/docs/)
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)

## ⚠️ Disclaimer

**Dieser Bot ist für Bildungszwecke gedacht. Verwenden Sie Live Trading auf eigene Gefahr. Vergangene Performance ist keine Garantie für zukünftige Ergebnisse.**
