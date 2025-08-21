import pandas as pd
import os
import glob

def find_original_well_data():
    """
    Find the original well data file that was used for the old deletion process.
    This should contain all wells (including the ones that were deleted).
    """
    print("Looking for original well data files...")
    
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
        print("Please place your original well data CSV file in this directory.")
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
        required_columns = ["Well Name", "API 14", "Production Method", "Perf Lateral Length"]
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

def simulate_old_deletion_process(df):
    """
    Simulate the old deletion process that removed wells ending in 0000.
    This shows which wells would have been deleted by the old method.
    """
    print("\nSimulating old deletion process (API 14 ending in 0000)...")
    
    # Create API10 column (first 10 digits of API 14)
    df["API10"] = df["API 14"].astype(str).str[:10]
    
    # Find duplicates based on API10
    duplicates = df[df.duplicated(subset=["API10"], keep=False)].sort_values(by="API10")
    
    if len(duplicates) == 0:
        print("No duplicate API10s found.")
        return None, None
    
    print(f"Found {len(duplicates)} wells with duplicate API10s")
    
    # Simulate old method: keep wells that DON'T end in 0000
    def keep_non_0000_wells(group):
        # Convert API 14 to string and check if it ends in 0000
        group["ends_in_0000"] = group["API 14"].astype(str).str.endswith("0000")
        
        # Keep wells that DON'T end in 0000
        wells_to_keep = group[~group["ends_in_0000"]]
        
        # If all wells end in 0000, keep the first one (fallback)
        if len(wells_to_keep) == 0:
            print(f"  Warning: All wells for API10 {group.iloc[0]['API10']} end in 0000, keeping first one")
            wells_to_keep = group.head(1)
        
        return wells_to_keep
    
    # Apply old method to duplicates
    kept_by_old_method = duplicates.groupby("API10", group_keys=False).apply(keep_non_0000_wells).reset_index(drop=True)
    
    # Find wells that would have been removed by old method
    all_duplicate_rows = duplicates.copy()
    kept_rows = kept_by_old_method.copy()
    
    # Create a composite key to identify which rows to remove
    all_duplicate_rows['composite_key'] = all_duplicate_rows['API10'] + '_' + all_duplicate_rows['API 14'].astype(str)
    kept_rows['composite_key'] = kept_rows['API10'] + '_' + kept_rows['API 14'].astype(str)
    
    # Remove the rows we want to keep from the list of rows to remove
    rows_removed_by_old_method = all_duplicate_rows[~all_duplicate_rows['composite_key'].isin(kept_rows['composite_key'])].copy()
    
    # Clean up temporary columns
    rows_removed_by_old_method = rows_removed_by_old_method.drop(columns=['composite_key', 'API10'])
    kept_rows = kept_rows.drop(columns=['composite_key', 'API10'])
    
    return kept_rows, rows_removed_by_old_method

def apply_new_perf_length_method(df):
    """
    Apply the new Perf Lateral Length method to the same dataset.
    """
    print("\nApplying new Perf Lateral Length method...")
    
    # Create API10 column (first 10 digits of API 14)
    df["API10"] = df["API 14"].astype(str).str[:10]
    
    # Find duplicates based on API10
    duplicates = df[df.duplicated(subset=["API10"], keep=False)].sort_values(by="API10")
    
    if len(duplicates) == 0:
        print("No duplicate API10s found.")
        return None, None
    
    # Group by API10 and find which wells should be kept
    def keep_highest_perf_length(group):
        # Convert Perf Lateral Length to numeric, handling any non-numeric values
        group["Perf Lateral Length"] = pd.to_numeric(group["Perf Lateral Length"], errors='coerce')
        
        # Find the row with the highest Perf Lateral Length
        max_length = group["Perf Lateral Length"].max()
        
        # If all values are NaN, keep all rows (no preference)
        if pd.isna(max_length):
            return group
        
        # Keep only the row(s) with the highest Perf Lateral Length
        return group[group["Perf Lateral Length"] == max_length]
    
    # Apply to duplicates - keep only the highest Perf Lateral Length for each API10
    filtered_duplicates = duplicates.groupby("API10", group_keys=False).apply(keep_highest_perf_length).reset_index(drop=True)
    
    # Find all rows that should be removed (duplicates minus the ones we kept)
    all_duplicate_rows = duplicates.copy()
    kept_rows = filtered_duplicates.copy()
    
    # Create a composite key to identify which rows to remove
    all_duplicate_rows['composite_key'] = all_duplicate_rows['API10'] + '_' + all_duplicate_rows['API 14'].astype(str)
    kept_rows['composite_key'] = kept_rows['API10'] + '_' + kept_rows['API 14'].astype(str)
    
    # Remove the rows we want to keep from the list of rows to remove
    rows_to_remove = all_duplicate_rows[~all_duplicate_rows['composite_key'].isin(kept_rows['composite_key'])].copy()
    
    # Clean up the temporary column
    rows_to_remove = rows_to_remove.drop(columns=['composite_key', 'API10'])
    kept_rows = kept_rows.drop(columns=['composite_key', 'API10'])
    
    return kept_rows, rows_to_remove

def compare_old_vs_new_methods(old_kept, old_removed, new_kept, new_removed, original_df):
    """
    Compare the old deletion method vs new Perf Lateral Length method.
    """
    print("\n" + "="*80)
    print("COMPARISON: Old Method (API 14 ending in 0000) vs New Method (Perf Lateral Length)")
    print("="*80)
    
    # Get API 14s from old and new methods
    old_removed_apis = set(old_removed["API 14"].astype(str))
    new_removed_apis = set(new_removed["API 14"].astype(str))
    
    # Find differences
    only_old_removed = old_removed_apis - new_removed_apis
    only_new_removed = new_removed_apis - old_removed_apis
    both_removed = old_removed_apis & new_removed_apis
    
    print(f"\nOld method (API 14 ending in 0000) would remove: {len(old_removed_apis)} wells")
    print(f"New method (Perf Lateral Length) would remove: {len(new_removed_apis)} wells")
    
    print(f"\nWells that would be removed by OLD method but NOT by NEW method:")
    print(f"Count: {len(only_old_removed)}")
    if only_old_removed:
        print("  These wells were incorrectly targeted by the old method:")
        for api in sorted(only_old_removed):
            well_info = original_df[original_df["API 14"].astype(str) == api]
            if not well_info.empty:
                well_name = well_info.iloc[0]["Well Name"]
                perf_length = well_info.iloc[0]["Perf Lateral Length"]
                api_14 = well_info.iloc[0]["API 14"]
                print(f"    API: {api_14}, Well: {well_name}, Perf Length: {perf_length}")
    
    print(f"\nWells that would NOT be removed by OLD method but SHOULD be removed by NEW method:")
    print(f"Count: {len(only_new_removed)}")
    if only_new_removed:
        print("  These wells were missed by the old method:")
        for api in sorted(only_new_removed):
            well_info = original_df[original_df["API 14"].astype(str) == api]
            if not well_info.empty:
                well_name = well_info.iloc[0]["Well Name"]
                perf_length = well_info.iloc[0]["Perf Lateral Length"]
                api_14 = well_info.iloc[0]["API 14"]
                print(f"    API: {api_14}, Well: {well_name}, Perf Length: {perf_length}")
    
    print(f"\nWells that would be correctly removed by BOTH methods:")
    print(f"Count: {len(both_removed)}")
    
    # Calculate accuracy
    total_old_removals = len(old_removed_apis)
    correct_removals = len(both_removed)
    accuracy = (correct_removals / total_old_removals * 100) if total_old_removals > 0 else 0
    
    print(f"\nAccuracy of old deletion method: {accuracy:.1f}%")
    print(f"  Correctly identified for removal: {correct_removals}")
    print(f"  Incorrectly targeted: {len(only_old_removed)}")
    print(f"  Missed removals: {len(only_new_removed)}")

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
    print("="*80)
    print("SIMULATING OLD DELETION PROCESS vs NEW PERF LATERAL LENGTH METHOD")
    print("="*80)
    print("This script will:")
    print("1. Simulate the old deletion process (removing wells ending in 0000)")
    print("2. Apply the new Perf Lateral Length method")
    print("3. Compare the results to see which wells were incorrectly targeted")
    print()
    
    # Step 1: Load original well data
    original_file = find_original_well_data()
    if not original_file:
        return
    
    original_df = load_well_data(original_file)
    if original_df is None:
        return
    
    # Extract project name for unique file labeling
    project_name = extract_project_name(original_file)
    print(f"\nProject identified: {project_name}")
    
    # Step 2: Simulate old deletion process
    old_kept, old_removed = simulate_old_deletion_process(original_df)
    
    if old_kept is None:
        print("No duplicates found to process.")
        return
    
    # Step 3: Apply new Perf Lateral Length method
    new_kept, new_removed = apply_new_perf_length_method(original_df)
    
    if new_kept is None:
        print("No duplicates found to process.")
        return
    
    # Step 4: Compare methods
    compare_old_vs_new_methods(old_kept, old_removed, new_kept, new_removed, original_df)
    
    # Step 5: Save results with project-specific filenames
    print("\nSaving results...")
    
    # Create unique filenames based on project
    old_kept_filename = f'wells_kept_by_old_method_{project_name}.csv'
    old_removed_filename = f'wells_removed_by_old_method_{project_name}.csv'
    new_kept_filename = f'wells_kept_by_new_method_{project_name}.csv'
    new_removed_filename = f'wells_removed_by_new_method_{project_name}.csv'
    
    # Save results from old method
    old_kept.to_csv(old_kept_filename, index=False)
    print(f"Saved {len(old_kept)} wells kept by old method: {old_kept_filename}")
    
    old_removed.to_csv(old_removed_filename, index=False)
    print(f"Saved {len(old_removed)} wells removed by old method: {old_removed_filename}")
    
    # Save results from new method
    new_kept.to_csv(new_kept_filename, index=False)
    print(f"Saved {len(new_kept)} wells kept by new method: {new_kept_filename}")
    
    new_removed.to_csv(new_removed_filename, index=False)
    print(f"Saved {len(new_removed)} wells removed by new method: {new_removed_filename}")
    
    # Step 6: Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Original dataset: {len(original_df)} wells")
    print(f"Wells with duplicate API10s: {len(original_df[original_df.duplicated(subset=original_df['API 14'].astype(str).str[:10], keep=False)])}")
    
    print(f"\nOld Method (API 14 ending in 0000):")
    print(f"  Wells kept: {len(old_kept)}")
    print(f"  Wells removed: {len(old_removed)}")
    
    print(f"\nNew Method (Perf Lateral Length):")
    print(f"  Wells kept: {len(new_kept)}")
    print(f"  Wells removed: {len(new_removed)}")
    
    print("\nFiles created:")
    print(f"1. {old_kept_filename} - Wells kept by old method")
    print(f"2. {old_removed_filename} - Wells removed by old method")
    print(f"3. {new_kept_filename} - Wells kept by new method")
    print(f"4. {new_removed_filename} - Wells removed by new method")
    
    print("\nRecommendation:")
    print("Review the comparison above to see which wells were incorrectly")
    print("targeted by the old method and which should have been targeted.")

if __name__ == "__main__":
    main()
