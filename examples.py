#!/usr/bin/env python3
"""
Example: How to use the Championship Analysis Tool programmatically

This shows how to integrate the tool into your own scripts or workflows.
"""

import subprocess
import sys
from pathlib import Path


def example_basic_usage():
    """Example 1: Basic usage - analyze one gender for a team"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Usage")
    print("="*70 + "\n")
    
    team_id = "405"  # Pittsburgh
    gender = "women"
    
    cmd = [
        sys.executable,
        "championship_workflow.py",
        "--team", team_id,
        "--gender", gender
    ]
    
    print(f"Command: {' '.join(cmd)}\n")
    subprocess.run(cmd)


def example_both_genders():
    """Example 2: Analyze both men and women"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Both Genders")
    print("="*70 + "\n")
    
    team_id = "405"
    
    cmd = [
        sys.executable,
        "championship_workflow.py",
        "--team", team_id
    ]
    
    print(f"Command: {' '.join(cmd)}\n")
    subprocess.run(cmd)


def example_interactive():
    """Example 3: Use the interactive tool"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Interactive Mode")
    print("="*70 + "\n")
    
    cmd = [sys.executable, "analyze_team.py"]
    
    print(f"Command: {' '.join(cmd)}\n")
    print("This will prompt you for team ID and gender...\n")
    subprocess.run(cmd)


def example_read_results():
    """Example 4: Read and process the results programmatically"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Reading Results")
    print("="*70 + "\n")
    
    import csv
    from pathlib import Path
    
    # Check if results exist
    acc_file = Path("swimmer_championship_comparison_acc.csv")
    ncaa_file = Path("swimmer_championship_comparison_ncaa.csv")
    
    if not acc_file.exists():
        print("❌ No results found. Run the workflow first!")
        return
    
    print("📊 Reading ACC results...\n")
    
    with open(acc_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Total entries: {len(rows)}")
    
    # Example: Find swimmers who are already faster than 8th place
    print("\n🏆 Swimmers already faster than ACC 8th place:\n")
    
    qualified = []
    for row in rows:
        if row.get('time_drop_to_8'):
            drop_needed = float(row['time_drop_to_8'])
            if drop_needed == 0:
                qualified.append({
                    'name': row['swimmer_name'],
                    'event': row['event'],
                    'time': row['best_time']
                })
    
    for entry in qualified[:10]:  # Show first 10
        print(f"  {entry['name']:<25} {entry['event']:<15} {entry['time']}")
    
    if len(qualified) > 10:
        print(f"\n  ... and {len(qualified) - 10} more!")
    
    print(f"\nTotal swimmers/events qualifying: {len(qualified)}")


def example_step_by_step():
    """Example 5: Run individual steps manually"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Manual Step-by-Step Execution")
    print("="*70 + "\n")
    
    team_id = "405"
    gender = "women"
    
    print("Step 1: Scrape swimmer IDs")
    subprocess.run([sys.executable, "scrape_swim_ids.py", team_id, gender])
    
    print("\nStep 2: Scrape swimmer events")
    gender_code = "F" if gender == "women" else "M"
    subprocess.run([sys.executable, "scrape_events.py", gender_code])
    
    print("\nStep 3: Scrape finals times (if needed)")
    print("Skipping - assuming files exist")
    
    print("\nStep 4: Run analysis")
    subprocess.run([sys.executable, "champ_roster_enhanced.py", gender])
    
    print("\n✅ Manual workflow complete!")


def main():
    """Main menu to run examples"""
    print("\n" + "*"*70)
    print("CHAMPIONSHIP ANALYSIS TOOL - EXAMPLES")
    print("*"*70)
    
    print("\nChoose an example to run:\n")
    print("  1) Basic usage - analyze one gender")
    print("  2) Analyze both men and women")
    print("  3) Interactive mode")
    print("  4) Read and process existing results")
    print("  5) Manual step-by-step execution")
    print("  0) Exit")
    
    choice = input("\nEnter choice (0-5): ").strip()
    
    examples = {
        "1": example_basic_usage,
        "2": example_both_genders,
        "3": example_interactive,
        "4": example_read_results,
        "5": example_step_by_step
    }
    
    if choice == "0":
        print("\nGoodbye!")
        return
    
    example_func = examples.get(choice)
    if example_func:
        example_func()
    else:
        print(f"\n❌ Invalid choice: {choice}")


if __name__ == "__main__":
    main()
