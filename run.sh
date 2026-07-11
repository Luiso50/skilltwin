#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/cerebro"
python server.py
