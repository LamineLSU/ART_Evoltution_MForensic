#!/usr/bin/env python3
"""
Android Runtime Structure Diff Tool

Compares structure definitions across different Android versions
to identify changes in classes, members, and memory layouts.

For detailed documentation, see README.md
"""

import sys
import json
import argparse
from datetime import datetime
import os


def load_json_data(version, arch, base_dir='.'):
    """
    Load structure data from a JSON file.
    
    Args:
        version (str): Android version (e.g., 'android9')
        arch (str): Architecture (e.g., 'arm32')
        base_dir (str): Base directory containing the JSON files
        
    Returns:
        dict: Structure data or None if file not found
    """
    filename = f"{version}_{arch}_structures.json"
    filepath = os.path.join(base_dir, filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
            print(f"Successfully loaded {filepath}")
            return data
    except FileNotFoundError:
        print(f"Error: File {filepath} not found")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {filepath}")
        return None
    except Exception as e:
        print(f"Error loading {filepath}: {str(e)}")
        return None


def validate_data(data, version, arch):
    """
    Validate that the data has the expected structure.
    
    Args:
        data (dict): The loaded JSON data
        version (str): Expected version
        arch (str): Expected architecture
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not data:
        return False
        
    if 'version' not in data or 'architecture' not in data or 'classes' not in data:
        print(f"Error: Invalid data format - missing required fields")
        return False
        
    if data['version'] != version:
        print(f"Warning: Version mismatch - expected {version}, got {data['version']}")
        
    expected_arch = f"{arch}_structures"
    if data['architecture'] != expected_arch:
        print(f"Warning: Architecture mismatch - expected {expected_arch}, got {data['architecture']}")
        
    return True


def compare_members(old_members, new_members):
    """
    Compare members between two versions of a class.
    
    Args:
        old_members (dict): Members from the old version
        new_members (dict): Members from the new version
        
    Returns:
        tuple: (added_members, removed_members, modified_offsets)
    """
    added_members = {}
    removed_members = {}
    modified_offsets = {}

    # Find added and modified members
    for member, new_offset in new_members.items():
        if member not in old_members:
            added_members[member] = new_offset
        elif old_members[member] != new_offset:
            modified_offsets[member] = {
                "old_offset": old_members[member],
                "new_offset": new_offset
            }

    # Find removed members
    for member, old_offset in old_members.items():
        if member not in new_members:
            removed_members[member] = old_offset

    return added_members, removed_members, modified_offsets


def compare_versions(version1_data, version2_data):
    """
    Compare two versions of structure data.
    
    Args:
        version1_data (dict): Data from the older version
        version2_data (dict): Data from the newer version
        
    Returns:
        dict: Comparison results
    """
    version1_classes = version1_data['classes']
    version2_classes = version2_data['classes']

    added_classes = {}
    removed_classes = {}
    modified_classes = {}

    # Find added and modified classes
    for class_name, new_class_data in version2_classes.items():
        if class_name not in version1_classes:
            added_classes[class_name] = new_class_data
        else:
            old_class_data = version1_classes[class_name]
            old_members = old_class_data.get('members', {})
            new_members = new_class_data.get('members', {})

            # Compare members
            added_members, removed_members, modified_offsets = compare_members(old_members, new_members)

            # Compare class sizes
            old_class_size = old_class_data.get('size')
            new_class_size = new_class_data.get('size')
            size_changed = old_class_size != new_class_size

            if added_members or removed_members or modified_offsets or size_changed:
                modified_classes[class_name] = {
                    "added_members": added_members,
                    "removed_members": removed_members,
                    "modified_offsets": modified_offsets,
                    "class_size_change": {
                        "old_size": old_class_size,
                        "new_size": new_class_size
                    } if size_changed else None
                }

    # Find removed classes
    for class_name, old_class_data in version1_classes.items():
        if class_name not in version2_classes:
            removed_classes[class_name] = old_class_data

    return {
        "added_classes": added_classes,
        "removed_classes": removed_classes,
        "modified_classes": modified_classes
    }


def generate_version_pairs(versions):
    """
    Generate adjacent version pairs from a list of versions.
    
    Args:
        versions (list): List of versions in order
        
    Returns:
        list: List of (ver1, ver2) tuples
    """
    return [(versions[i], versions[i+1]) for i in range(len(versions)-1)]


def parse_version_pair(pair_str):
    """
    Parse a version pair string in the format "ver1,ver2".
    
    Args:
        pair_str (str): String in format "ver1,ver2"
        
    Returns:
        tuple: (ver1, ver2) or None if invalid
    """
    parts = pair_str.split(',')
    if len(parts) != 2:
        print(f"Error: Invalid version pair format: {pair_str}. Expected 'ver1,ver2'")
        return None
    return (parts[0], parts[1])


def get_version_pairs(args):
    """
    Get version pairs to compare based on command-line arguments.
    
    Args:
        args: Command-line arguments
        
    Returns:
        list: List of (ver1, ver2, arch) tuples to compare
    """
    pairs = []
    
    # Process --range
    if args.range:
        # Get all versions in the range
        start_idx = args.versions.index(args.range[0])
        end_idx = args.versions.index(args.range[1])
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
            
        versions_in_range = args.versions[start_idx:end_idx+1]
        version_pairs = generate_version_pairs(versions_in_range)
        
        for ver1, ver2 in version_pairs:
            pairs.append((ver1, ver2, args.arch))
    
    # Process --pairs
    if args.pairs:
        for pair_str in args.pairs:
            pair = parse_version_pair(pair_str)
            if pair:
                ver1, ver2 = pair
                if ver1 in args.versions and ver2 in args.versions:
                    pairs.append((ver1, ver2, args.arch))
                else:
                    print(f"Warning: One or both versions in {pair_str} not found in available versions")
    
    # If no pairs specified, compare all sequential versions
    if not pairs and not args.range and not args.pairs:
        version_pairs = generate_version_pairs(args.versions)
        for ver1, ver2 in version_pairs:
            pairs.append((ver1, ver2, args.arch))
    
    return pairs


def summarize_changes(comparison_result):
    """
    Generate a summary of the changes found.
    
    Args:
        comparison_result (dict): The comparison result
        
    Returns:
        dict: Summary statistics
    """
    added_class_count = len(comparison_result["added_classes"])
    removed_class_count = len(comparison_result["removed_classes"])
    modified_class_count = len(comparison_result["modified_classes"])
    
    added_member_count = 0
    removed_member_count = 0
    modified_offset_count = 0
    size_change_count = 0
    
    for class_data in comparison_result["modified_classes"].values():
        added_member_count += len(class_data["added_members"])
        removed_member_count += len(class_data["removed_members"])
        modified_offset_count += len(class_data["modified_offsets"])
        if class_data["class_size_change"]:
            size_change_count += 1
    
    return {
        "added_classes": added_class_count,
        "removed_classes": removed_class_count,
        "modified_classes": modified_class_count,
        "added_members": added_member_count,
        "removed_members": removed_member_count,
        "modified_offsets": modified_offset_count,
        "size_changes": size_change_count,
        "total_changes": (added_class_count + removed_class_count + modified_class_count +
                         added_member_count + removed_member_count + modified_offset_count)
    }


def main():
    """
    Main function to parse command line arguments and process version comparisons.
    """
    parser = argparse.ArgumentParser(
        description='Compare Android Runtime structure definitions across versions',
        epilog="For detailed usage examples and documentation, see README.md"
    )
    
    # Required arguments
    parser.add_argument('--arch', required=True,
                      help='Architecture to analyze (e.g., arm32, arm64, x86_32, x86_64)')
    parser.add_argument('--input-dir', default='.',
                      help='Directory containing the structure JSON files')
    parser.add_argument('-o', '--output', required=True,
                      help='Path where the diff JSON file will be written')
    
    # Version specification options
    parser.add_argument('--versions', nargs='+', default=[f'android{i}' for i in range(9, 15)],
                      help='List of available versions (default: android9-android14)')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'),
                      help='Compare all sequential pairs in version range (e.g., --range android9 android14)')
    parser.add_argument('--pairs', nargs='+', metavar='VER1,VER2',
                      help='Specific version pairs to compare (e.g., --pairs android9,android11 android10,android14)')
    
    args = parser.parse_args()
    
    # Always measure time
    start_time = datetime.now()
    print(f"Started comparison at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get the version pairs to compare
        version_pairs = get_version_pairs(args)
        
        if not version_pairs:
            print("Error: No valid version pairs to compare")
            return 1
            
        print(f"Will compare {len(version_pairs)} version pairs:")
        for ver1, ver2, arch in version_pairs:
            print(f"  {ver1} vs {ver2} ({arch})")
        
        # Perform comparisons
        comparison_report = {}
        
        for ver1, ver2, arch in version_pairs:
            print(f"\nComparing {ver1} vs {ver2} ({arch})...")
            
            # Load data
            ver1_data = load_json_data(ver1, arch, args.input_dir)
            ver2_data = load_json_data(ver2, arch, args.input_dir)
            
            if not ver1_data or not ver2_data:
                print(f"Error: Could not compare {ver1} vs {ver2}")
                continue
                
            if not validate_data(ver1_data, ver1, arch) or not validate_data(ver2_data, ver2, arch):
                print(f"Error: Invalid data format, skipping comparison")
                continue
            
            # Compare versions
            comparison_result = compare_versions(ver1_data, ver2_data)
            
            # Add to report
            comparison_key = f"{ver1} vs {ver2}"
            comparison_report[comparison_key] = comparison_result
            
            # Summarize changes
            summary = summarize_changes(comparison_result)
            print(f"Comparison summary for {ver1} vs {ver2} ({arch}):")
            print(f"  Added classes: {summary['added_classes']}")
            print(f"  Removed classes: {summary['removed_classes']}")
            print(f"  Modified classes: {summary['modified_classes']}")
            print(f"  Added members: {summary['added_members']}")
            print(f"  Removed members: {summary['removed_members']}")
            print(f"  Modified offsets: {summary['modified_offsets']}")
            print(f"  Size changes: {summary['size_changes']}")
            print(f"  Total changes: {summary['total_changes']}")
        
        # Save the report to JSON
        with open(args.output, 'w', encoding='utf-8') as outfile:
            json.dump(comparison_report, outfile, indent=4)
            
        print(f"\nComparison report saved to {args.output}")
        
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    # Calculate and display execution time
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"Total execution time: {duration} (finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
