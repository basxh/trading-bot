# 🤖 Modular Trading Bot

Ein modulärer Trading Bot in Python für Backtesting, Paper Trading und Live Trading.

## 📁 Projektstruktur

```
trading-bot/
├── trading_bot.py       # Haupt-Script mit CLI
├── config.json          # Konfigurationsdatei
├── data_fetcher.py      # Marktdaten-Modul
├── strategies.py        # Strategie-Modul
├── backtest.py          # Backtest-Modul
├── paper_trader.py      # Paper Trading Modul
├── live_trader.py       # Live Trading Vorbereitung
├── requirements.txt     # Python Abhängigkeiten
└── README.md           # Diese Datei
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
- **Combined**: Kombination aus SMA + RSI
- Einfach erweiterbar für eigene Strategien

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
    "stop_loss_pct": 0.02       // 2% Stop Loss
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
- **Paper Mode**: Testen ohne echtes Geld
- **Konfirmation**: Live Trading erfordert manuelle Bestätigung

## 📁 Erzeugte Dateien

- `data/*.csv` - Heruntergeladene Marktdaten
- `data/paper_trades_*.db` - SQLite Datenbank mit Trades
- `logs/trading_bot.log` - Ausführliches Logging
- `reports/*` - Backtest Reports und Charts

## 🧪 Testing

```bash
# Test mit verschiedenen Strategien
python trading_bot.py --mode backtest --symbol AAPL --strategy sma_crossover --save-report --plot
python trading_bot.py --mode backtest --symbol AAPL --strategy rsi --save-report --plot
python trading_bot.py --mode backtest --symbol AAPL --strategy combined --save-report --plot

# Crypto
python trading_bot.py --mode backtest --symbol BTC-USD --market-type crypto --strategy sma_crossover
```

## 📚 Weiterführende Links

- [yfinance Dokumentation](https://github.com/ranaroussi/yfinance)
- [Alpaca API](https://alpaca.markets/docs/)
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)

## ⚠️ Disclaimer

**Dieser Bot ist für Bildungszwecke gedacht. Verwenden Sie Live Trading auf eigene Gefahr. Vergangene Performance ist keine Garantie für zukünftige Ergebnisse.**
