#!/usr/bin/env python3
"""
Simple Championship Analysis Tool
For non-technical users to easily generate championship comparisons

Just run: python analyze_team.py
"""

import sys
import subprocess
from pathlib import Path


def get_input(prompt: str, default: str = None) -> str:
    """Get user input with optional default"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default


def main():
    """Interactive championship analysis"""
    print("\n" + "="*70)
    print("🏊 CHAMPIONSHIP ANALYSIS TOOL")
    print("="*70 + "\n")
    
    print("This tool will analyze your team's times against championship standards.")
    print("It will generate Excel-ready CSV files with time comparisons.\n")
    
    # Get team ID
    print("Step 1: Enter your team's SwimCloud ID")
    print("  (Find it in the team's SwimCloud URL)")
    print("  Example: For Pitt, the URL is swimcloud.com/team/405, so enter '405'\n")
    
    team_id = get_input("Team ID", "405")
    
    # Get gender
    print("\n" + "-"*70)
    print("Step 2: Which swimmers do you want to analyze?")
    print("  1) Women only")
    print("  2) Men only")
    print("  3) Both men and women\n")
    
    choice = get_input("Enter choice (1/2/3)", "3")
    
    gender_map = {
        "1": "women",
        "2": "men",
        "3": None
    }
    
    gender = gender_map.get(choice)
    gender_text = "both men and women" if gender is None else gender
    
    # Confirm
    print("\n" + "-"*70)
    print("Ready to start analysis:")
    print(f"  Team ID: {team_id}")
    print(f"  Gender: {gender_text}")
    print("-"*70 + "\n")
    
    confirm = get_input("Start analysis? (y/n)", "y").lower()
    
    if confirm != "y":
        print("\n❌ Analysis cancelled.")
        return
    
    # Run the workflow
    print("\n🚀 Starting analysis workflow...\n")
    
    cmd = [sys.executable, "championship_workflow.py", "--team", team_id]
    if gender:
        cmd.extend(["--gender", gender])
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("\n" + "="*70)
            print("✅ SUCCESS!")
            print("="*70)
            print("\nYour analysis files are ready:")
            print("  • swimmer_championship_comparison_acc.csv")
            print("  • swimmer_championship_comparison_ncaa.csv")
            print("\nOpen these files in Excel to view the results!")
            print("="*70 + "\n")
        else:
            print("\n❌ Analysis failed. Please check the error messages above.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
