#!/bin/bash

# Source and destination directories
SRC_DIR="/Users/amangotchu/Documents/Kotlin-bench/patches"
DEST_DIR="/Users/amangotchu/Documents/landing/public/patches"

# Make sure the destination directory exists
mkdir -p "$DEST_DIR"

# Iterate through the immediate subdirectories of the source directory
for subdir in "$SRC_DIR"/*; do
    if [ -d "$subdir" ]; then
        base_name=$(basename "$subdir")
        echo "Processing $base_name..."
        
        # Create the corresponding subdirectory in the destination
        mkdir -p "$DEST_DIR/$base_name"
        
        # Copy all subdirectories except "original"
        for nested_dir in "$subdir"/*; do
            if [ -d "$nested_dir" ]; then
                nested_name=$(basename "$nested_dir")
                if [ "$nested_name" != "original" ]; then
                    echo "  Copying $base_name/$nested_name"
                    cp -R "$nested_dir" "$DEST_DIR/$base_name/"
                else
                    echo "  Skipping $base_name/original"
                fi
            fi
        done
    fi
done

echo "Copy completed!"