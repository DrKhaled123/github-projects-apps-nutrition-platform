#!/bin/bash
# Utility script to write to shared memory from any AI agent

MEMORY_BASE="./ai-agents-shared-memory"
CATEGORY="$1"
KEY="$2"
VALUE="$3"
AGENT="${4:-$(basename "$0")}"

if [ -z "$CATEGORY" ] || [ -z "$KEY" ] || [ -z "$VALUE" ]; then
    echo "Usage: $0 <category> <key> <value> [agent]"
    echo "Categories: context, knowledge, tasks, history"
    exit 1
fi

# Use Python memory manager
python3 "${MEMORY_BASE}/utils/memory_manager.py" write \
    --category "$CATEGORY" \
    --key "$KEY" \
    --data "$VALUE" \
    --agent "$AGENT"

echo "✓ Written to shared memory: ${CATEGORY}/${KEY}"
