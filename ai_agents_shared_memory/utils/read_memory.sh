#!/bin/bash
# Utility script to read from shared memory from any AI agent

MEMORY_BASE="./ai-agents-shared-memory"
CATEGORY="$1"
KEY="$2"

if [ -z "$CATEGORY" ]; then
    echo "Usage: $0 <category> [key]"
    echo "Categories: context, knowledge, tasks, history"
    exit 1
fi

# Use Python memory manager
if [ -z "$KEY" ]; then
    # Query all in category
    python3 "${MEMORY_BASE}/utils/memory_manager.py" query --category "$CATEGORY"
else
    # Read specific key
    python3 "${MEMORY_BASE}/utils/memory_manager.py" read --category "$CATEGORY" --key "$KEY"
fi
