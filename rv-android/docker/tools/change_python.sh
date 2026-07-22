#!/bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <directory>"
  exit 1
fi

directory="$1"

string1="\/usr\/bin\/python"
string2="python "
replacement1="\/usr\/bin\/python2"
replacement2="python2 "

find "$directory" -type f -print0 | while IFS= read -r -d '' file; do
    if [[ "$file" =~ \.(rb|py|sh)$ ]]; then
        sed -i "s/$string1/$replacement1/g; s/$string2/$replacement2/g" "$file"
    fi
done