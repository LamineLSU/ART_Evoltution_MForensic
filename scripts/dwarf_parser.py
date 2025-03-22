#!/usr/bin/env python3
"""
DWARF Symbol Parser for Android Runtime (ART) Library

Extracts structure definitions from libart.so and outputs them in JSON format
suitable for Android memory forensics analysis.

For detailed documentation, see README.md
"""

import sys
import json
import argparse
from elftools.elf.elffile import ELFFile
from datetime import datetime


def parse_elf_symbols(filename):
    """
    Extract DWARF information from an ELF file.
    
    Args:
        filename (str): Path to the ELF file to analyze
        
    Returns:
        dwarf_info: DWARF information object or None if not found
    """
    try:
        with open(filename, 'rb') as f:
            elffile = ELFFile(f)
            
            if not elffile.has_dwarf_info():
                print("Error: No DWARF information found in the file")
                return None

            return elffile.get_dwarf_info()
    except FileNotFoundError:
        print(f"Error: File {filename} not found")
        return None
    except Exception as e:
        print(f"Error: Failed to parse ELF file: {str(e)}")
        return None


def parse_object(die, structures):
    """
    Extract class/struct information from a DIE and add it to the structures dictionary.
    
    Args:
        die: A DWARF information entry representing a class or structure
        structures (dict): Dictionary to store extracted structure information
        
    Returns:
        str: Name of the parsed object
    """
    # Extract name or use "UnNamed" default
    name_attr = die.attributes.get('DW_AT_name')
    name = "UnNamed" if name_attr is None else name_attr.value.decode('utf-8')
    
    # Extract size
    size_attr = die.attributes.get('DW_AT_byte_size')
    size = None if size_attr is None else size_attr.value
    
    # Initialize structure in our dictionary
    if name not in structures:
        structures[name] = {
            "size": f"0x{size:x}" if size is not None else "Unknown",
            "members": {}
        }
    
    return name


def process_children(die, structures, parent_name):
    """
    Process all children of a DIE, extracting member information.
    
    Args:
        die: The parent DIE whose children to process
        structures (dict): Dictionary to store extracted structure information
        parent_name (str): Name of the parent structure
    """
    for child in die.iter_children():
        if str(child.tag) != 'DW_TAG_member':
            continue
            
        # For members, we're interested in those with a location (non-constants)
        location_attr = child.attributes.get('DW_AT_data_member_location')
        if location_attr is None:
            continue  # Skip constants or other entries without a location
            
        # Get member name
        name_attr = child.attributes.get('DW_AT_name')
        name = "UnNamed" if name_attr is None else name_attr.value.decode('utf-8')
        
        # Add member to parent structure
        offset = location_attr.value
        structures[parent_name]["members"][name] = offset


def process_die(die, structures):
    """
    Process a DIE to extract relevant information based on its tag.
    
    Args:
        die: The DWARF information entry to process
        structures (dict): Dictionary to store extracted structure information
    """
    if str(die.tag) not in ['DW_TAG_class_type', 'DW_TAG_structure_type']:
        return
    
    # Parse the object and get its name
    name = parse_object(die, structures)
    
    # Process its members if it has children
    if die.has_children:
        process_children(die, structures, name)


def parse_dwarf_info(dwarf_info):
    """
    Iterate through all DIEs in all compilation units to extract structure information.
    
    Args:
        dwarf_info: The DWARF information object to parse
        
    Returns:
        dict: Dictionary containing all extracted structure information
    """
    structures = {}
    
    for cu in dwarf_info.iter_CUs():
        for die in cu.iter_DIEs():
            process_die(die, structures)
    
    return structures


def main():
    """
    Main function to parse command line arguments and process the ELF file.
    """
    parser = argparse.ArgumentParser(
        description='Parse DWARF debug symbols from libart.so to extract structure information in JSON format',
        epilog="For detailed usage examples and documentation, see README.md"
    )
    parser.add_argument('filepath', help='Path to the libart.so file to analyze')
    parser.add_argument('--version', required=True, 
                       help='Android version identifier (e.g., android9, android10)')
    parser.add_argument('--arch', required=True, 
                       help='Target architecture (e.g., arm32, arm64, x86_32, x86_64)')
    parser.add_argument('-o', '--output', required=True, 
                       help='Path where the JSON output file will be written')
    
    args = parser.parse_args()
    
    # Always measure time
    start_time = datetime.now()
    print(f"Started processing at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Extract and parse DWARF information
        print(f"Processing DWARF information from: {args.filepath}")
        dwarf_info = parse_elf_symbols(args.filepath)
        if not dwarf_info:
            return 1
            
        # Parse the DWARF info into a structured dictionary
        print("Extracting structure information...")
        structures = parse_dwarf_info(dwarf_info)
        
        # Create the final output
        output = {
            "version": args.version,
            "architecture": f"{args.arch}_structures",
            "classes": structures
        }
        
        # Write to the output file
        print(f"Writing JSON data to: {args.output}")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=4)
            
        print(f"Successfully wrote structure information to {args.output}")
        print(f"Extracted {len(structures)} structures")
        
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
