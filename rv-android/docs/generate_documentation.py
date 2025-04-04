#!/usr/bin/env python3
"""
Script to convert PlantUML diagrams to images and embed them in markdown documentation.

This script:
1. Finds all PlantUML (.puml) files in the images directory
2. Converts them to SVG or PNG using the plantuml package
3. Updates markdown files to embed the images instead of referencing them

Requirements:
    pip install plantuml markdown
"""

import os
import re
import sys
import base64
import plantuml
from pathlib import Path
import markdown
import argparse
from typing import List, Dict, Tuple, Optional

# Constants
DOCS_DIR = Path('/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs')
IMAGES_DIR = DOCS_DIR / 'images'


def find_plantuml_files(directory: Path) -> List[Path]:
    """Find all PlantUML files in the directory."""
    return list(directory.glob('**/*.puml'))


def convert_to_svg(plantuml_file: Path, output_dir: Optional[Path] = None) -> Tuple[Path, bytes]:
    """Convert PlantUML file to SVG and return the path and content."""
    # If output_dir not specified, use the same directory as the PlantUML file
    if output_dir is None:
        output_dir = plantuml_file.parent
    
    # Create PlantUML client
    plantuml_client = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/svg/')
    
    # Get SVG content
    svg_content = plantuml_client.processes_file(str(plantuml_file))
    
    # Create output file path
    svg_file = output_dir / f"{plantuml_file.stem}.svg"
    
    # Write SVG content to file
    with open(svg_file, 'wb') as f:
        f.write(svg_content)
    
    return svg_file, svg_content


def convert_to_png(plantuml_file: Path, output_dir: Optional[Path] = None) -> Tuple[Path, bytes]:
    """Convert PlantUML file to PNG and return the path and content."""
    # If output_dir not specified, use the same directory as the PlantUML file
    if output_dir is None:
        output_dir = plantuml_file.parent
    
    # Create PlantUML client
    plantuml_client = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/png/')
    
    # Get PNG content
    png_content = plantuml_client.processes_file(str(plantuml_file))
    
    # Create output file path
    png_file = output_dir / f"{plantuml_file.stem}.png"
    
    # Write PNG content to file
    with open(png_file, 'wb') as f:
        f.write(png_content)
    
    return png_file, png_content


def convert_all_plantuml_files(directory: Path, output_format: str = 'svg') -> Dict[str, Path]:
    """Convert all PlantUML files in directory to the specified format and return a mapping of file stems to output paths."""
    plantuml_files = find_plantuml_files(directory)
    file_mapping = {}
    
    print(f"Converting {len(plantuml_files)} PlantUML files to {output_format}...")
    
    for plantuml_file in plantuml_files:
        try:
            if output_format.lower() == 'svg':
                output_file, _ = convert_to_svg(plantuml_file)
            else:
                output_file, _ = convert_to_png(plantuml_file)
            
            file_mapping[plantuml_file.stem] = output_file
            print(f"Converted {plantuml_file.name} to {output_file.name}")
        except Exception as e:
            print(f"Error converting {plantuml_file.name}: {e}")
    
    return file_mapping


def update_markdown_references(markdown_file: Path, file_mapping: Dict[str, Path], embed: bool = False) -> int:
    """
    Update markdown file to reference or embed the generated images.
    
    Returns the number of replacements made.
    """
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    replacements = 0
    
    # Regular expression to find PlantUML references
    # This pattern matches both ![alt](path/to/file.puml) and ![alt](path/to/file.png)
    pattern = r'!\[(.*?)\]\((.*?)(?:\.puml|\.png|\.svg)\)'
    
    for match in re.finditer(pattern, content):
        alt_text = match.group(1)
        path = match.group(2)
        
        # Extract the file stem (filename without extension)
        file_stem = os.path.basename(path)
        
        # If the file stem is in our mapping, update the reference
        for puml_stem, output_path in file_mapping.items():
            if puml_stem in file_stem:
                relative_path = os.path.relpath(output_path, markdown_file.parent)
                
                if embed and output_path.suffix.lower() == '.svg':
                    # Read SVG content and embed it directly
                    with open(output_path, 'r', encoding='utf-8') as f:
                        svg_content = f.read()
                    replacement = f'<div class="embedded-diagram">\n{svg_content}\n</div>'
                elif embed and output_path.suffix.lower() == '.png':
                    # Read PNG content and embed it as base64
                    with open(output_path, 'rb') as f:
                        png_content = f.read()
                    b64_content = base64.b64encode(png_content).decode('utf-8')
                    replacement = f'<img src="data:image/png;base64,{b64_content}" alt="{alt_text}">'
                else:
                    # Just update the reference path
                    replacement = f'![{alt_text}]({relative_path})'
                
                content = content.replace(match.group(0), replacement)
                replacements += 1
                break
    
    # Only write if changes were made
    if content != original_content:
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return replacements


def find_markdown_files(directory: Path) -> List[Path]:
    """Find all markdown files in the directory."""
    return list(directory.glob('**/*.md'))


def update_all_markdown_files(directory: Path, file_mapping: Dict[str, Path], embed: bool = False) -> int:
    """
    Update all markdown files in directory to reference or embed the generated images.
    
    Returns the total number of replacements made.
    """
    markdown_files = find_markdown_files(directory)
    total_replacements = 0
    
    print(f"Updating {len(markdown_files)} markdown files...")
    
    for markdown_file in markdown_files:
        try:
            replacements = update_markdown_references(markdown_file, file_mapping, embed)
            if replacements > 0:
                print(f"Updated {markdown_file.name} with {replacements} replacements")
            total_replacements += replacements
        except Exception as e:
            print(f"Error updating {markdown_file.name}: {e}")
    
    return total_replacements


def main():
    parser = argparse.ArgumentParser(description='Convert PlantUML diagrams to images and embed them in markdown documentation.')
    parser.add_argument('--format', choices=['svg', 'png'], default='svg', help='Output format (default: svg)')
    parser.add_argument('--embed', action='store_true', help='Embed images directly in markdown files')
    parser.add_argument('--dir', type=str, default=str(DOCS_DIR), help='Root directory to process')
    
    args = parser.parse_args()
    
    root_dir = Path(args.dir)
    images_dir = root_dir / 'images'
    
    if not root_dir.exists():
        print(f"Error: Directory {root_dir} does not exist.")
        return 1
    
    if not images_dir.exists():
        print(f"Error: Images directory {images_dir} does not exist.")
        return 1
    
    # Convert PlantUML files
    file_mapping = convert_all_plantuml_files(images_dir, args.format)
    
    if not file_mapping:
        print("No PlantUML files were converted.")
        return 0
    
    # Update markdown files
    total_replacements = update_all_markdown_files(root_dir, file_mapping, args.embed)
    
    print(f"Completed: {len(file_mapping)} files converted, {total_replacements} references updated.")
    return 0


if __name__ == '__main__':
    sys.exit(main())