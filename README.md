# Android Runtime Structures Evolution Dataset

This repository contains a comprehensive dataset of Android Runtime (ART) structure evolution across Android versions 9-14 for four architectures (ARM64, ARM32, x86_64, x86_32). The dataset is derived from our systematic study examining the evolution patterns of runtime structures and their implications for memory forensics.

## Dataset Overview

Our analysis covers:
- 6 Android versions (9 through 14)
- 4 architectures (ARM64, ARM32, x86_64, x86_32)
- Complete structure information from libart.so
- 34 critical structures essential for memory forensics
- Detailed evolution analysis between consecutive versions

## Repository Structure

Each architecture directory contains:

1. `structures/`: Complete structure information extracted from libart.so for each Android version
2. `forensic_structures/`: The 34 critical structures essential for memory forensics
3. `diffs/`: Evolution analysis showing structural changes between consecutive versions

## Data Format

### Structure Files
The JSON files in `structures/` and `forensic_structures/` contain:
- Structure names and sizes
- Member information (offsets, types, sizes)
- Additional metadata specific to each structure

### Evolution Diffs
The `evolution_diffs.json` files analyze changes to the 34 critical structures essential for memory forensics between consecutive versions. For each version transition (9->10, 10->11, 11->12, 12->13, 13->14), the diffs track:

1. Structure Modifications:
   - Structure removals (when a critical structure is no longer present)
   - Size changes in existing structures
   
2. Member-Level Changes:
   - Member additions and removals within critical structures
   - Offset modifications for existing members
   - Detailed mapping of member relocations with old and new positions

These diffs focus specifically on structures crucial for memory forensics operations including thread enumeration, heap analysis, and object recovery. The tracked changes help understand how runtime evolution impacts forensic tool reliability and maintenance.