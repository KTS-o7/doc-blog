#!/bin/bash

# Usage: ./new_md.sh "My Post Title"

# Get title either from param or by asking user
if [ -z "$1" ]; then
  read -p "📝 Enter the post title: " TITLE
else
  TITLE="$1"
fi

# Ensure title is not empty
if [ -z "$TITLE" ]; then
  echo "❌ Title cannot be empty!"
  exit 1
fi

# Current date/time in ISO-8601 with timezone offset
DATE=$(date +"%Y-%m-%dT%H:%M:%S%z" | sed -E 's/([0-9]{2})([0-9]{2})$/\1:\2/')

# List directories inside ./content
echo "📂 Available directories in ./content:"
dirs=(./content/*/)
select DIR in "${dirs[@]}"; do
  if [ -n "$DIR" ]; then
    echo "✅ You chose: $DIR"
    break
  else
    echo "❌ Invalid choice, try again."
  fi
done

# Generate filename from title (slugify with underscores)
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g' | sed -E 's/^_+|_+$//g')
FILE="${DIR}${SLUG}.md"

# Write the markdown front matter
cat > "$FILE" <<EOF
+++
title = '$TITLE'
date = $DATE
draft = false
math = true
+++
EOF

echo "🎉 Markdown file created: $FILE"
