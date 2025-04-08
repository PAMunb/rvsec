#!/bin/bash
# Script to convert PlantUML files to PNG using the PlantUML server

echo "Converting PlantUML files to PNG..."

# Check if first argument is provided
if [ "$1" != "" ]; then
    echo "Converting pattern: $1"
    pattern="$1"
else
    echo "Converting all .puml files"
    pattern="*.puml"
fi

# Loop through PlantUML files matching pattern
for puml_file in $pattern; do
    # Check if file exists and is a regular file
    if [ -f "$puml_file" ]; then
        # Extract file name without extension
        file_name="${puml_file%.puml}"
        
        # Output PNG file name
        png_file="${file_name}.png"
        
        echo "Converting $puml_file to $png_file..."
        
        # Use Python's plantuml module from the virtualenv
        python -c "
import plantuml
import sys

puml_file = '$puml_file'
png_file = '$png_file'

try:
    # Create PlantUML client
    plantuml_client = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/png/')
    
    # Get PNG content
    png_content = plantuml_client.processes_file(puml_file)
    
    # Write PNG content to file
    with open(png_file, 'wb') as f:
        f.write(png_content)
    
    print(f'Successfully converted {puml_file} to {png_file}')
    
except Exception as e:
    print(f'Error converting {puml_file}: {e}')
    sys.exit(1)
"
        # Check if conversion was successful
        if [ $? -ne 0 ]; then
            echo "Error converting $puml_file to $png_file"
        fi
    fi
done

echo "Conversion complete!"