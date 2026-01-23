#!/bin/bash
# Backup script for refactoring workflow
# Usage: ./backup.sh <file_path> [backup_dir]

set -e

FILE_PATH="$1"
BACKUP_DIR="${2:-backup}"
DATE=$(date +%Y%m%d_%H%M%S)

if [ -z "$FILE_PATH" ]; then
    echo "Usage: $0 <file_path> [backup_dir]"
    echo "Example: $0 src/module/file.py backup"
    exit 1
fi

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File not found: $FILE_PATH"
    exit 1
fi

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Get filename without path
FILENAME=$(basename "$FILE_PATH")

# Create backup with timestamp
BACKUP_PATH="$BACKUP_DIR/${FILENAME%.py}_${DATE}.py"

cp "$FILE_PATH" "$BACKUP_PATH"

echo "Backup created: $BACKUP_PATH"
echo ""
echo "To restore:"
echo "  cp $BACKUP_PATH $FILE_PATH"
