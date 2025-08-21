# ComboCurve Duplicate Well Removal Script

A Python script to identify and remove duplicate wells from ComboCurve projects using a sophisticated three-tier priority system.

## Features

- **Automated duplicate detection** based on API10 (first 10 digits of API 14)
- **Three-tier priority system** for selecting the best well to keep
- **CSV output** with wells to keep and wells to remove
- **Project-specific file naming** for easy organization
- **Robust error handling** for missing columns and permission issues

## Priority System

The script uses a three-tier priority system to determine which well to keep when duplicates are found:

### 1. **First Priority: Last Prod Date Monthly**
- Keep wells with the **most recent production date**
- Most recent production indicates active wells

### 2. **Second Priority: Perf Lateral Length**
- Among wells with the **same production date**, keep the one with **highest Perf Lateral Length**
- Longer lateral lengths typically indicate better well performance

### 3. **Third Priority: API14 Ending**
- Among wells with the **same production date AND same Perf Lateral Length**, prefer wells where the **API14 does NOT end in "0000"**
- API14 ending in "0000" often indicates placeholder or dummy records

## Requirements

- Python 3.6+
- pandas
- CSV files with well data

## Required Columns

The script expects the following columns in your CSV file:
- `Well Name`
- `API 14`
- `Production Method`
- `Perf Lateral Length`
- `Last Prod Date Monthly`

## Usage

1. **Place your well data CSV file** in the same directory as the script
2. **Run the script**:
   ```bash
   python simple_dup_removal.py
   ```
3. **Select your file** from the list of available CSV files
4. **Review the output**:
   - `wells_to_keep_[project_name].csv` - Wells that should be kept
   - `wells_to_remove_[project_name].csv` - Wells that should be removed
5. filter your CC project on wells to remove > then remove all

## Example Output

```
============================================================
SIMPLE PERF LATERAL LENGTH DUPLICATE REMOVAL
============================================================
This script will find duplicate wells and keep the best one for each API10:
1. First priority: Wells with the most recent Last Prod Date Monthly
2. Second priority: Among wells with same date, highest Perf Lateral Length
3. Third priority: Among wells with same length, prefer API14 NOT ending in '0000'

Looking for well data files...
Found the following well data files:
1. well_02___Delaware_Recent_PDP_20250806060537.csv

Enter the number of the file to use (1-1): 1
Selected: well_02___Delaware_Recent_PDP_20250806060537.csv

Project identified: Delaware_Recent_PDP

Loading well data from well_02___Delaware_Recent_PDP_20250806060537.csv...
Successfully loaded 1500 wells

Finding duplicate wells using Perf Lateral Length and Last Prod Date...
Found 45 wells with duplicate API10s

Saving results...
Saved 25 wells to keep: wells_to_keep_Delaware_Recent_PDP.csv
Saved 20 wells to remove: wells_to_remove_Delaware_Recent_PDP.csv

============================================================
SUMMARY
============================================================
Original dataset: 1500 wells
Wells with duplicate API10s: 45
Wells to keep: 25
Wells to remove: 20

Files created:
1. wells_to_keep_Delaware_Recent_PDP.csv - Wells that should be kept
2. wells_to_remove_Delaware_Recent_PDP.csv - Wells that should be removed

The wells in the 'removed' file are duplicates that should be
removed from your project, keeping only the best well for each API10:
- Priority 1: Most recent Last Prod Date Monthly
- Priority 2: Highest Perf Lateral Length (if dates are equal)
- Priority 3: API14 NOT ending in '0000' (if lengths are equal)
```

## File Structure

```
project/
├── simple_dup_removal.py          # Main script
├── README.md                      # This file
├── well_data.csv                  # Your input file
├── wells_to_keep_[project].csv    # Output: wells to keep
└── wells_to_remove_[project].csv  # Output: wells to remove
```

## Error Handling

The script includes robust error handling for:
- Missing required columns
- Permission errors when saving files
- Invalid file selections
- Empty or corrupted CSV files

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is for internal use at ComboCurve.
