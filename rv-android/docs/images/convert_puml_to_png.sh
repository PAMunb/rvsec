#!/bin/bash
# Script to convert PlantUML files to PNG using the PlantUML online server

echo "Converting PlantUML files to PNG..."

# Check if first argument is provided
if [ "$1" != "" ]; then
    echo "Converting pattern: $1"
    pattern="$1"
else
    echo "Converting all .puml files"
    pattern="*.puml"
fi

# Function to encode PlantUML for server URL
encode_plantuml() {
    local plantuml_text="$1"
    echo "$plantuml_text" | gzip -9 -f | xxd -p | tr -d '\n'
}

# Loop through PlantUML files matching pattern
for puml_file in $pattern; do
    # Check if file exists and is a regular file
    if [ -f "$puml_file" ]; then
        # Extract file name without extension
        file_name="${puml_file%.puml}"
        
        # Output PNG file name
        png_file="${file_name}.png"
        
        echo "Converting $puml_file to $png_file..."
        
        # Read the PlantUML content
        puml_content=$(cat "$puml_file")
        
        # Encode the content for PlantUML server URL
        encoded=$(encode_plantuml "$puml_content")
        
        # Download the PNG directly from the PlantUML server
        curl -s "http://www.plantuml.com/plantuml/png/~h$encoded" > "$png_file"
        
        # Check if conversion was successful
        if [ -s "$png_file" ]; then
            echo "Successfully converted $puml_file to $png_file"
        else
            echo "Error converting $puml_file to $png_file"
            # Remove empty file
            rm "$png_file"
        fi
    fi
done

echo "Conversion complete!"