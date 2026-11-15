#!/bin/zsh
cd "$(dirname "$0")"
python3 scripts/start.py
if [ $? -ne 0 ]; then
  echo "Mulec could not start. See the message above. Press Enter to close."
  read
fi
