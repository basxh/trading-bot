# Trading Bot Entwicklung - Lessons Learned

## Zusammenfassung

**Datum:** 2026-04-19
**Phase:** Phase 2 - Fehlerbehebung & Stabilisierung
**Test:** ETH 6h → Trading Bot v2 mit 2h Test

---

## Was funktioniert ✅

### 1. Bot-Struktur
- Logging-Framework funktioniert
- Datei-Struktur ist korrekt
- Konfiguration über JSON/Args möglich

### 2. Datenabruf (yfinance)
- ETH-USD, BTC-USD, AAPL Daten verfügbar
- 15m, 1h, 1d Timeframes funktionieren
- Zuverlässiger Abruf ohne API-Key

### 3. Neue Strategie (Trading Bot v2)
- Vereinfachte Adaptive Momentum Strategie
- RSI + EMA Crossover
- Generiert tatsächlich Signale!
- RSI 64.9 > 60 → SELL Signal funktioniert

### 4. Vereinfachtes Paper Trading
- Keine komplexe SQLite-DB
- JSONL-Logging für Trades und Status
- Einfache Positionsverwaltung

---

## Was NICHT funktioniert ❌

### 1. Original ETH 6h Test (07:11-13:11)
- **0 Trades in 6 Stunden**
- Preise wurden im Log angezeigt, aber Report zeigt immer 0.0
- Strategie hat keine Signale generiert
- Ursache: Zu konservative Parameter (RSI 30/70, ATR 0.8)

### 2. Komplexe SQLite-Datenbank
- Schwierig zu debuggen
- Keine Transparenz was passiert
- Fehler werden verschluckt

### 3. Original-Code Struktur
- Zu viele Abhängigkeiten
- Keine Pre-Flight Tests
- Silent failures

---

## Neue Herangehensweise

### Prinzip: "Start Simple, Then Scale"

1. **Daten-Test (5 Min)**
   ```bash
   python3 -c "import yfinance; df = yfinance.download('ETH-USD', period='5d', interval='15m'); print(f'Got {len(df)} candles')"
   ```

2. **Strategie-Backtest (5 Min)**
   - Teste auf historischen Daten
   - Validiere Signale
   - Passe Parameter

3. **Paper Trading 1-2h (kurz)**
   - Starte mit kleinem Zeitfenster
   - Beobachte erste Trades
   - Dann: 24h Test

4. **Live Trading (nur nach Erfolg)**
   - Nach profitablen 24h Paper Tests
   - Mit kleinem Capital starten

---

## Empfohlene Pipeline

```
┌─────────────────┐
│  1. Daten-Test  │  (5 Min) - yfinance OK?
└────────┬────────┘
         ▼
┌─────────────────┐
│  2. Strategie   │  (5 Min) - Signale vorhanden?
│    Backtest     │
└────────┬────────┘
         ▼
┌─────────────────┐
│  3. Paper 2h    │  (2h) - Erste echte Trades?
└────────┬────────┘
         ▼
┌─────────────────┐
│  4. Paper 24h   │  (24h) - Profitabel?
└────────┬────────┘
         ▼
┌─────────────────┐
│  5. Live $100   │  (Tage) - Funktioniert echt?
└────────┬────────┘
         ▼
┌─────────────────┐
│  6. Scale Up    │  (Wochen) - Mehr Capital
└─────────────────┘
```

---

## Parameter-Empfehlungen

### Für mehr Signale (aktiver Trading):
```python
rsi_overbought = 60  # statt 70
rsi_oversold = 40    # statt 30
atr_multiplier = 0.5 # statt 0.8
timeframe = '15m'    # statt '1h'
```

### Für weniger, aber stärkere Signale:
```python
rsi_overbought = 70
rsi_oversold = 30
atr_multiplier = 1.0
timeframe = '1h'
```

---

## Technische Erkenntnisse

### yfinance vs ccxt
- **yfinance:** Einfacher, funktioniert direkt, keine API-Key nötig
- **ccxt:** Braucht Installation (externally-managed environment), aber echtzeit-näher

### Logging
- JSONL-Format > SQLite für Debugging
- Einfach zu parsen, menschenlesbar
- Jede Minute Status-Update wichtig

### Fehlerbehandlung
- Pre-Flight Checks sind essentiell
- Bei Fehler sofort beenden
- Keine Silent Failures

---

## Nächste Schritte

1. ✅ Trading Bot v2 läuft (2h Test gestartet 13:41)
2. 📊 Ergebnisse auswerten (nach ~15:41)
3. 🔄 Bei Erfolg: 24h Test planen
4. 🚀 Bei Profit: Live Trading

---

## Änderungen in v2

| Feature | Alt | Neu |
|---------|-----|-----|
| Datenquelle | eigener fetcher | yfinance |
| Datenbank | SQLite | JSONL |
| Strategie | MomentumBreakout | SimpleAdaptive |
| Tests | Keine | Pre-Flight |
| Logging | Komplex | Einfach |
| Fehler | Silent | Explizit |

---

**Erstellt:** 2026-04-19 13:45
**Autor:** Echelon (Subagent)
