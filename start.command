#!/bin/zsh
# Double-click this file in Finder to start FitLog and open it in your browser.
cd "$(dirname "$0")" || exit 1
exec python3 app.py
