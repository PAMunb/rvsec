#!/bin/bash
# Script to convert PlantUML files to SVG using PlantUML server

echo "Converting PlantUML files to SVG..."

# Loop through all PlantUML files
for puml_file in *.puml; do
    # Extract file name without extension
    file_name="${puml_file%.puml}"
    
    # Output SVG file name
    svg_file="${file_name}.svg"
    
    echo "Converting $puml_file to $svg_file..."
    
    # Use plantuml.jar directly if available (better option)
    if command -v plantuml &> /dev/null; then
        plantuml -tsvg "$puml_file"
        echo "Created $svg_file using local PlantUML"
    else
        # Alternative approach - use the PlantUML server directly with the file
        echo "Local PlantUML not found, using PlantUML server..."
        curl -s --data-urlencode "text@$puml_file" "http://www.plantuml.com/plantuml/svg/" > "$svg_file"
        echo "Created $svg_file using PlantUML server"
    fi
done

echo "Conversion complete!"