#!/bin/bash
echo "============================================"
echo " DAVID CHAMBERS — Legal Website Server v3"
echo "============================================"
echo " Website: http://localhost:8000"
cd "$(dirname "$0")"
pip3 install -r requirements.txt -q
python3 main.py
