#!/bin/bash
cd /data/.openclaw/workspace/projects/trading-bot
python3 btc_6h_paper_test.py 2>&1 | tee logs/btc_6h_test.log