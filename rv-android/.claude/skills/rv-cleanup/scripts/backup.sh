#!/bin/bash
# Backup script for cleanup workflow
# Usage: ./backup.sh <module-name>

set -e

MODULE="$1"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/cleanup_${DATE}"

if [ -z "$MODULE" ]; then
    echo "Usage: $0 <module-name>"
    echo "Example: $0 rv-agent"
    exit 1
fi

MODULE_PATH="modules/${MODULE}/src"

if [ ! -d "$MODULE_PATH" ]; then
    echo "Error: Module not found: $MODULE_PATH"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Copy all Python files
echo "Backing up $MODULE_PATH to $BACKUP_DIR..."
find "$MODULE_PATH" -name "*.py" -exec cp --parents {} "$BACKUP_DIR/" \;

# Count files backed up
COUNT=$(find "$BACKUP_DIR" -name "*.py" | wc -l)

echo ""
echo "Backup complete:"
echo "  Location: $BACKUP_DIR"
echo "  Files: $COUNT Python files"
echo ""
echo "To restore:"
echo "  cp -r $BACKUP_DIR/$MODULE_PATH/* $MODULE_PATH/"
