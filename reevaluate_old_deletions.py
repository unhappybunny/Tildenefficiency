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

def find_old_deletion_file():
    """
    Find the old deletion file that shows which wells were removed.
    """
    print("\nLooking for old deletion files...")
    
    # Get all CSV files that contain deletion keywords
    all_csv_files = glob.glob("*.csv")
    deletion_files = []
    
    for file in all_csv_files:
        if any(keyword in file.lower() for keyword in ["deleted", "removed", "duplicate"]):
            deletion_files.append(file)
    
    # Remove duplicates and sort
    deletion_files = sorted(list(set(deletion_files)))
    
    if not deletion_files:
        print("No old deletion files found.")
        print("If you have a file showing which wells were deleted, please place it in this directory.")
        return None
    
    print("Found the following deletion files:")
    for i, file in enumerate(deletion_files, 1):
        print(f"{i}. {file}")
    
    # Let user choose which file to use
    while True:
        try:
            choice = input(f"\nEnter the number of the file to use (1-{len(deletion_files)}): ")
            choice = int(choice)
            if 1 <= choice <= len(deletion_files):
                selected_file = deletion_files[choice - 1]
                print(f"Selected: {selected_file}")
                return selected_file
            else:
                print("Invalid choice. Please enter a valid number.")
        except ValueError:
            print("Please enter a valid number.")

def revaluate_duplicates_with_perf_length(df):
    """
    Re-evaluate duplicates using Perf Lateral Length instead of API 14 ending in 0000.
    """
    print("\nRe-evaluating duplicates using Perf Lateral Length...")
    
    # Create API10 column (first 10 digits of API 14)
    df["API10"] = df["API 14"].astype(str).str[:10]
    
    # Find duplicates based on API10
    duplicates = df[df.duplicated(subset=["API10"], keep=False)].sort_values(by="API10")
    
    if len(duplicates) == 0:
        print("No duplicate API10s found.")
        return None, None
    
    print(f"Found {len(duplicates)} wells with duplicate API10s")
    
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

def analyze_old_vs_new_deletions(original_df, old_deletion_df, new_deletion_df):
    """
    Compare old deletion method vs new Perf Lateral Length method.
    """
    print("\n" + "="*60)
    print("ANALYSIS: Old vs New Deletion Method")
    print("="*60)
    
    if old_deletion_df is None:
        print("No old deletion data available for comparison.")
        return
    
    # Get API 14s from old deletions
    old_deleted_apis = set(old_deletion_df["API 14"].astype(str))
    new_deleted_apis = set(new_deletion_df["API 14"].astype(str))
    
    # Find differences
    only_old_deleted = old_deleted_apis - new_deleted_apis
    only_new_deleted = new_deleted_apis - old_deleted_apis
    both_deleted = old_deleted_apis & new_deleted_apis
    
    print(f"\nOld deletion method removed {len(old_deleted_apis)} wells")
    print(f"New Perf Lateral Length method would remove {len(new_deleted_apis)} wells")
    
    print(f"\nWells that were deleted by OLD method but should NOT be deleted by NEW method:")
    print(f"Count: {len(only_old_deleted)}")
    if only_old_deleted:
        for api in sorted(only_old_deleted):
            well_info = original_df[original_df["API 14"].astype(str) == api]
            if not well_info.empty:
                well_name = well_info.iloc[0]["Well Name"]
                perf_length = well_info.iloc[0]["Perf Lateral Length"]
                print(f"  API: {api}, Well: {well_name}, Perf Length: {perf_length}")
    
    print(f"\nWells that were NOT deleted by OLD method but SHOULD be deleted by NEW method:")
    print(f"Count: {len(only_new_deleted)}")
    if only_new_deleted:
        for api in sorted(only_new_deleted):
            well_info = original_df[original_df["API 14"].astype(str) == api]
            if not well_info.empty:
                well_name = well_info.iloc[0]["Well Name"]
                perf_length = well_info.iloc[0]["Perf Lateral Length"]
                print(f"  API: {api}, Well: {well_name}, Perf Length: {perf_length}")
    
    print(f"\nWells that were correctly deleted by BOTH methods:")
    print(f"Count: {len(both_deleted)}")
    
    # Calculate accuracy
    total_old_deletions = len(old_deleted_apis)
    correct_deletions = len(both_deleted)
    accuracy = (correct_deletions / total_old_deletions * 100) if total_old_deletions > 0 else 0
    
    print(f"\nAccuracy of old deletion method: {accuracy:.1f}%")
    print(f"  Correctly deleted: {correct_deletions}")
    print(f"  Incorrectly deleted: {len(only_old_deleted)}")
    print(f"  Missed deletions: {len(only_new_deleted)}")

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
    print("RE-EVALUATING OLD DUPLICATE WELL DELETIONS")
    print("="*60)
    print("This script will re-evaluate old duplicate well deletions using")
    print("Perf Lateral Length instead of the old API 14 ending in 0000 method.")
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
    
    # Step 2: Load old deletion data (optional)
    old_deletion_file = find_old_deletion_file()
    old_deletion_df = None
    if old_deletion_file:
        old_deletion_df = load_well_data(old_deletion_file)
    
    # Step 3: Re-evaluate duplicates using Perf Lateral Length
    kept_wells, wells_to_remove = revaluate_duplicates_with_perf_length(original_df)
    
    if kept_wells is None:
        print("No duplicates found to re-evaluate.")
        return
    
    # Step 4: Save results with project-specific filenames
    print("\nSaving results...")
    
    # Create unique filenames based on project
    kept_filename = f'wells_to_keep_perf_length_{project_name}.csv'
    removed_filename = f'wells_to_remove_perf_length_{project_name}.csv'
    
    # Save wells that should be kept
    kept_wells.to_csv(kept_filename, index=False)
    print(f"Saved {len(kept_wells)} wells to keep: {kept_filename}")
    
    # Save wells that should be removed
    wells_to_remove.to_csv(removed_filename, index=False)
    print(f"Saved {len(wells_to_remove)} wells to remove: {removed_filename}")
    
    # Step 5: Analyze differences if old deletion data is available
    if old_deletion_df is not None:
        analyze_old_vs_new_deletions(original_df, old_deletion_df, wells_to_remove)
    
    # Step 6: Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Original dataset: {len(original_df)} wells")
    print(f"Wells with duplicate API10s: {len(original_df[original_df.duplicated(subset=original_df['API 14'].astype(str).str[:10], keep=False)])}")
    print(f"Wells to keep: {len(kept_wells)}")
    print(f"Wells to remove: {len(wells_to_remove)}")
    
    print("\nFiles created:")
    print(f"1. {kept_filename} - Wells that should be kept")
    print(f"2. {removed_filename} - Wells that should be removed")
    
    if old_deletion_df is not None:
        print("\nRecommendation:")
        print("Review the analysis above to see which wells were incorrectly")
        print("deleted by the old method and which should have been deleted.")

if __name__ == "__main__":
    main()
