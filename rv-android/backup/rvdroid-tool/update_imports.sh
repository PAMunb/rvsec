#!/bin/bash

# Define the base directory for the rvdroid-tool module
BASE_DIR="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rvdroid-tool/src/rvdroid_tool"

# Define the import mappings
declare -A mappings
mappings["from rvandroid.config.component_configurator"]="from rv_android_core.config.component_configurator"
mappings["from rvandroid.domain.static"]="from rv_android_core.domain.static"
mappings["from rvandroid.domain.classes"]="from rv_android_core.domain.classes"
mappings["from rvandroid.domain.window"]="from rv_android_core.domain.window"
mappings["from rvandroid.domain.wtg"]="from rv_android_core.domain.wtg"
mappings["from rvandroid.domain.widget"]="from rv_android_core.domain.widget"
mappings["from rvandroid.parser.log.logcat_parser"]="from rv_android_core.parser.log.logcat_parser"
mappings["from rvandroid.parser.screen.visitor.model"]="from rv_screen_parser.parser.screen.visitor.model"
mappings["from rvandroid.util.error"]="from rv_android_core.util.error"
mappings["from rvandroid.util.logging"]="from rv_android_core.util.logging"
mappings["from rvandroid.util.performance_monitor"]="from rv_android_core.util.performance_monitor"
mappings["from rvandroid.llm.language_model"]="from rv_llm.llm.language_model"
mappings["from rvandroid.rvdroid"]="from rvdroid_tool"

# Iterate over all Python files in the base directory
find "$BASE_DIR" -name "*.py" | while read -r file; do
    echo "Processing file: $file"
    for old_import in "${!mappings[@]}"; do
        new_import="${mappings[$old_import]}"
        # Use sed to replace the old import with the new one
        # The 'g' flag ensures all occurrences in a line are replaced
        # The 'i' flag for in-place editing
        # Using a different delimiter (e.g., '#') for sed to avoid issues with '/' in paths
        sed -i "s#${old_import}#${new_import}#g" "$file"
    done
done

echo "Import replacement complete."
