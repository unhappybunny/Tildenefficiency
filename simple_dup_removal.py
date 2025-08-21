import pandas as pd
import os
import glob

def find_well_data_file():
    """
    Find the well data file to process.
    """
    print("Looking for well data files...")
    
    # Get all CSV files in current directory
    all_csv_files = glob.glob("*.csv")
    
    # Filter to only well data files (exclude deletion files)
    well_data_files = []
    for file in all_csv_files:
        # Skip files that are clearly deletion files
        if any(keyword in file.lower() for keyword in ["deleted", "removed", "duplicate"]):
            continue
        # Include files that look like well data
        if any(keyword in file.lower() for keyword in ["well", "delaware", "eagleford", "midland"]):
            well_data_files.append(file)
    
    # Remove duplicates and sort
    well_data_files = sorted(list(set(well_data_files)))
    
    if not well_data_files:
        print("No well data files found in current directory.")
        print("Please place your well data CSV file in this directory.")
        return None
    
    print("Found the following well data files:")
    for i, file in enumerate(well_data_files, 1):
        print(f"{i}. {file}")
    
    # Let user choose which file to use
    while True:
        try:
            choice = input(f"\nEnter the number of the file to use (1-{len(well_data_files)}): ")
            choice = int(choice)
            if 1 <= choice <= len(well_data_files):
                selected_file = well_data_files[choice - 1]
                print(f"Selected: {selected_file}")
                return selected_file
            else:
                print("Invalid choice. Please enter a valid number.")
        except ValueError:
            print("Please enter a valid number.")

def load_well_data(file_path):
    """Load the well data from CSV file."""
    try:
        print(f"Loading well data from {file_path}...")
        df = pd.read_csv(file_path)
        print(f"Successfully loaded {len(df)} wells")
        
        # Check if required columns exist
        required_columns = ["Well Name", "API 14", "Production Method", "Perf Lateral Length", "Last Prod Date Monthly"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Warning: Missing required columns: {missing_columns}")
            print("Available columns:", list(df.columns))
            
            # Try to find similar column names
            for missing_col in missing_columns:
                similar_cols = [col for col in df.columns if missing_col.lower() in col.lower()]
                if similar_cols:
                    print(f"  Similar to '{missing_col}': {similar_cols}")
        
        return df
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def find_duplicates_by_perf_length(df):
    """
    Find duplicate wells based on API10 and keep the one with highest Perf Lateral Length,
    unless a shorter lateral length has a more recent production date.
    """
    print("\nFinding duplicate wells using Perf Lateral Length and Last Prod Date...")
    
    # Create API10 column (first 10 digits of API 14)
    df["API10"] = df["API 14"].astype(str).str[:10]
    
    # Find duplicates based on API10
    duplicates = df[df.duplicated(subset=["API10"], keep=False)].sort_values(by="API10")
    
    if len(duplicates) == 0:
        print("No duplicate API10s found.")
        return None, None
    
    print(f"Found {len(duplicates)} wells with duplicate API10s")
    
    # Group by API10 and find which wells should be kept
    def keep_best_well(group):
        # Convert Perf Lateral Length to numeric, handling any non-numeric values
        group["Perf Lateral Length"] = pd.to_numeric(group["Perf Lateral Length"], errors='coerce')
        
        # Convert Last Prod Date Monthly to datetime, handling any non-date values
        group["Last Prod Date Monthly"] = pd.to_datetime(group["Last Prod Date Monthly"], errors='coerce')
        
        # If all Perf Lateral Length values are NaN, keep all rows (no preference)
        if group["Perf Lateral Length"].isna().all():
            return group
        
        # If all Last Prod Date values are NaN, fall back to Perf Lateral Length
        if group["Last Prod Date Monthly"].isna().all():
            max_length = group["Perf Lateral Length"].max()
            wells_with_max_length = group[group["Perf Lateral Length"] == max_length]
            
            # If multiple wells have the same max length, prefer the one that doesn't end in "0000"
            if len(wells_with_max_length) > 1:
                # Check which wells don't end in "0000"
                wells_not_ending_0000 = wells_with_max_length[
                    wells_with_max_length["API 14"].astype(str).str[-4:] != "0000"
                ]
                
                # If there are wells that don't end in "0000", keep those
                if len(wells_not_ending_0000) > 0:
                    return wells_not_ending_0000
                else:
                    # If all end in "0000", keep all (no preference)
                    return wells_with_max_length
            else:
                return wells_with_max_length
        
        # Find the latest production date
        latest_date = group["Last Prod Date Monthly"].max()
        
        # Find wells with the latest production date
        wells_with_latest_date = group[group["Last Prod Date Monthly"] == latest_date]
        
        # Among wells with the latest date, find the one with highest Perf Lateral Length
        if len(wells_with_latest_date) > 1:
            max_length = wells_with_latest_date["Perf Lateral Length"].max()
            wells_with_max_length = wells_with_latest_date[wells_with_latest_date["Perf Lateral Length"] == max_length]
            
            # If multiple wells have the same max length, prefer the one that doesn't end in "0000"
            if len(wells_with_max_length) > 1:
                # Check which wells don't end in "0000"
                wells_not_ending_0000 = wells_with_max_length[
                    wells_with_max_length["API 14"].astype(str).str[-4:] != "0000"
                ]
                
                # If there are wells that don't end in "0000", keep those
                if len(wells_not_ending_0000) > 0:
                    return wells_not_ending_0000
                else:
                    # If all end in "0000", keep all (no preference)
                    return wells_with_max_length
            else:
                return wells_with_max_length
        else:
            return wells_with_latest_date
    
    # Apply to duplicates - keep the best well for each API10
    kept_wells = duplicates.groupby("API10", group_keys=False).apply(keep_best_well).reset_index(drop=True)
    
    # Find all rows that should be removed (duplicates minus the ones we kept)
    all_duplicate_rows = duplicates.copy()
    
    # Create a composite key to identify which rows to remove
    all_duplicate_rows['composite_key'] = all_duplicate_rows['API10'] + '_' + all_duplicate_rows['API 14'].astype(str)
    kept_wells['composite_key'] = kept_wells['API10'] + '_' + kept_wells['API 14'].astype(str)
    
    # Remove the rows we want to keep from the list of rows to remove
    wells_to_remove = all_duplicate_rows[~all_duplicate_rows['composite_key'].isin(kept_wells['composite_key'])].copy()
    
    # Clean up the temporary columns
    wells_to_remove = wells_to_remove.drop(columns=['composite_key', 'API10'])
    kept_wells = kept_wells.drop(columns=['composite_key', 'API10'])
    
    return kept_wells, wells_to_remove

def extract_project_name(filename):
    """Extract project name from filename for better file labeling."""
    # Remove file extension
    name = os.path.splitext(filename)[0]
    
    # Look for common project identifiers
    project_identifiers = [
        "Delaware", "Eagleford", "Midland", "PDP", "Legacy", "Recent",
        "Spraberry", "WC", "West", "East", "North", "South"
    ]
    
    found_identifiers = []
    for identifier in project_identifiers:
        if identifier.lower() in name.lower():
            found_identifiers.append(identifier)
    
    if found_identifiers:
        return "_".join(found_identifiers)
    else:
        # Use first part of filename if no identifiers found
        return name.split("_")[0] if "_" in name else name

def main():
    print("="*60)
    print("SIMPLE PERF LATERAL LENGTH DUPLICATE REMOVAL")
    print("="*60)
    print("This script will find duplicate wells and keep the best one for each API10:")
    print("1. First priority: Wells with the most recent Last Prod Date Monthly")
    print("2. Second priority: Among wells with same date, highest Perf Lateral Length")
    print("3. Third priority: Among wells with same length, prefer API14 NOT ending in '0000'")
    print()
    
    # Step 1: Load well data
    well_file = find_well_data_file()
    if not well_file:
        return
    
    df = load_well_data(well_file)
    if df is None:
        return
    
    # Extract project name for unique file labeling
    project_name = extract_project_name(well_file)
    print(f"\nProject identified: {project_name}")
    
    # Step 2: Find duplicates using Perf Lateral Length
    kept_wells, wells_to_remove = find_duplicates_by_perf_length(df)
    
    if kept_wells is None:
        print("No duplicates found to process.")
        return
    
    # Step 3: Save results
    print("\nSaving results...")
    
    # Create unique filenames based on project
    kept_filename = f'wells_to_keep_{project_name}.csv'
    removed_filename = f'wells_to_remove_{project_name}.csv'
    
    # Save wells that should be kept
    kept_wells.to_csv(kept_filename, index=False)
    print(f"Saved {len(kept_wells)} wells to keep: {kept_filename}")
    
    # Save wells that should be removed
    wells_to_remove.to_csv(removed_filename, index=False)
    print(f"Saved {len(wells_to_remove)} wells to remove: {removed_filename}")
    
    # Step 4: Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Original dataset: {len(df)} wells")
    print(f"Wells with duplicate API10s: {len(df[df.duplicated(subset=['API10'], keep=False)])}")
    print(f"Wells to keep: {len(kept_wells)}")
    print(f"Wells to remove: {len(wells_to_remove)}")
    
    print("\nFiles created:")
    print(f"1. {kept_filename} - Wells that should be kept")
    print(f"2. {removed_filename} - Wells that should be removed")
    
    print("\nThe wells in the 'removed' file are duplicates that should be")
    print("removed from your project, keeping only the best well for each API10:")
    print("- Priority 1: Most recent Last Prod Date Monthly")
    print("- Priority 2: Highest Perf Lateral Length (if dates are equal)")
    print("- Priority 3: API14 NOT ending in '0000' (if lengths are equal)")

if __name__ == "__main__":
    main()
