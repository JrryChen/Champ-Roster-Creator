#!/usr/bin/env python3
"""
Championship Analysis Workflow
Automates the complete process from team ID to final championship comparison analysis

Usage:
    python championship_workflow.py --team 405 --gender women
    python championship_workflow.py --team 405 --gender men
    python championship_workflow.py --team 405  # Both genders
"""

import argparse
import asyncio
import subprocess
import sys
import os
import time
import csv
from pathlib import Path
from typing import Optional

# Import NCAA invite times
sys.path.insert(0, str(Path(__file__).parent))
from ncaa_invite_times import w_invite_2025_codes, m_invite_2025_codes


class ChampionshipWorkflow:
    """Orchestrates the complete championship analysis workflow"""
    
    def __init__(self, team_id: str, gender: Optional[str] = None):
        self.team_id = team_id
        self.gender = gender  # "men", "women", or None for both
        self.base_dir = Path(__file__).parent
    
    def parse_time_to_seconds(self, time_str: str) -> Optional[float]:
        """Convert time string (MM:SS.xx or SS.xx) to seconds - reused from champ_roster.py"""
        if not time_str or not isinstance(time_str, str) or time_str == 'N/A':
            return None
        
        time_str = time_str.strip()
        
        # Try MM:SS.xx format
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                try:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
                except ValueError:
                    return None
        
        # Try SS.xx format
        try:
            return float(time_str)
        except ValueError:
            return None
    
    def get_invite_standard(self, event: str, gender: str) -> Optional[float]:
        """Get NCAA invite standard for an event - reused pattern from champ_roster.py"""
        # Map event string like "100 Back" to event code like "2|100|1"
        stroke_map = {
            'free': '1',
            'back': '2',
            'breast': '3',
            'fly': '4',
            'im': '5'
        }
        
        parts = event.lower().split()
        if len(parts) < 2:
            return None
        
        distance = parts[0]
        stroke = parts[1]
        
        stroke_code = stroke_map.get(stroke)
        if not stroke_code:
            return None
        
        event_code = f"{stroke_code}|{distance}|1"
        
        # Use same logic as get_invite_standard in champ_roster.py
        if gender.lower() in ["women", "f", "female"]:
            return w_invite_2025_codes.get(event_code)
        else:
            return m_invite_2025_codes.get(event_code)
    
    def add_ncaa_cut_times_to_csv(self, csv_file: str, gender: str):
        """Add NCAA cut times column to existing CSV"""
        csv_path = self.base_dir / csv_file
        if not csv_path.exists():
            return
        
        print(f"  📊 Adding NCAA cut times to {csv_file}...")
        
        # Read existing CSV
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)
            for row in reader:
                rows.append(row)
        
        # Skip if already has time_to_ncaa_cut column
        if 'time_to_ncaa_cut' in fieldnames:
            print(f"  ⏭️  Already has NCAA cut times column")
            return
        
        # Add time_to_ncaa_cut column after season_best
        new_fieldnames = []
        for field in fieldnames:
            new_fieldnames.append(field)
            if field == 'season_best':
                new_fieldnames.append('time_to_ncaa_cut')
        
        # For combined CSV, need to determine gender per row
        if gender == "both":
            # Load swimmer lists to determine gender
            swimmer_genders = {}
            for gender_code in ["M", "F"]:
                csv_file_path = self.base_dir / f"{gender_code}_swimmers.csv"
                if csv_file_path.exists():
                    with open(csv_file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for swimmer_row in reader:
                            swimmer_id = swimmer_row.get('Swimmer ID', '').strip()
                            swimmer_genders[swimmer_id] = "women" if gender_code == "F" else "men"
        
        # Calculate NCAA cut times for each row
        for row in rows:
            event = row.get('event', '')
            best_time = row.get('best_time', '')
            swimmer_id = row.get('swimmer_id', '')
            
            # Determine gender for this row
            row_gender = gender
            if gender == "both":
                row_gender = swimmer_genders.get(swimmer_id, "women")  # default to women if not found
            
            swim_seconds = self.parse_time_to_seconds(best_time)
            invite_standard = self.get_invite_standard(event, row_gender)
            
            if swim_seconds and invite_standard:
                diff = swim_seconds - invite_standard
                # If faster than standard, show 0, otherwise show time difference
                if diff < 0:
                    row['time_to_ncaa_cut'] = 0
                else:
                    row['time_to_ncaa_cut'] = round(diff, 2)
            else:
                row['time_to_ncaa_cut'] = 'N/A'
        
        # Write back to CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=new_fieldnames, restval='')
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"  ✅ Added NCAA cut times column")
        
    def print_step(self, step_num: int, total_steps: int, description: str):
        """Print formatted step information"""
        print(f"\n{'='*70}")
        print(f"STEP {step_num}/{total_steps}: {description}")
        print(f"{'='*70}\n")
    
    def run_script(self, script_name: str, args: list = None) -> int:
        """Run a Python script with arguments"""
        cmd = [sys.executable, str(self.base_dir / script_name)]
        if args:
            cmd.extend(args)
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=self.base_dir)
        return result.returncode
    
    def check_files_exist(self, file_patterns: list) -> bool:
        """Check if required files exist"""
        for pattern in file_patterns:
            files = list(self.base_dir.glob(pattern))
            if not files:
                print(f"❌ Missing required file: {pattern}")
                return False
        return True
    
    def step_1_scrape_swimmer_ids(self) -> bool:
        """Step 1: Scrape swimmer IDs from team roster"""
        self.print_step(1, 5, "Scraping Swimmer IDs from Team Roster")
        
        genders_to_process = []
        if self.gender is None:
            genders_to_process = ["men", "women"]
        else:
            genders_to_process = [self.gender]
        
        for gender in genders_to_process:
            print(f"\n📋 Fetching {gender.title()} swimmers...")
            result = self.run_script("scrape_swim_ids.py", [self.team_id, gender])
            if result != 0:
                print(f"❌ Failed to scrape {gender} swimmer IDs")
                return False
            
            # Check output file
            gender_code = "F" if gender == "women" else "M"
            csv_file = f"{gender_code}_swimmers.csv"
            if not (self.base_dir / csv_file).exists():
                print(f"❌ Output file {csv_file} not created")
                return False
            
            print(f"✅ Successfully scraped {gender} swimmers to {csv_file}")
            time.sleep(2)  # Brief pause between genders
        
        return True
    
    def step_2_scrape_swimmer_events(self) -> bool:
        """Step 2: Scrape individual events for each swimmer"""
        self.print_step(2, 5, "Scraping Individual Events for Each Swimmer")
        
        genders_to_process = []
        if self.gender is None:
            genders_to_process = ["M", "F"]
        else:
            genders_to_process = ["F" if self.gender == "women" else "M"]
        
        for gender_code in genders_to_process:
            gender_name = "Women" if gender_code == "F" else "Men"
            print(f"\n📊 Fetching events for {gender_name} swimmers...")
            
            result = self.run_script("scrape_events.py", [gender_code])
            if result != 0:
                print(f"❌ Failed to scrape {gender_name} swimmer events")
                return False
            
            # Check output directory and files
            output_dir = f"{gender_code}_Events"
            if not (self.base_dir / output_dir).exists():
                print(f"❌ Output directory {output_dir} not created")
                return False
            
            all_events_file = self.base_dir / output_dir / f"all_{gender_code}_Events.json"
            if not all_events_file.exists():
                print(f"❌ Combined events file not created: {all_events_file}")
                return False
            
            print(f"✅ Successfully scraped {gender_name} swimmer events to {output_dir}/")
            time.sleep(2)  # Brief pause between genders
        
        return True
    
    def step_3_scrape_finals_times(self) -> bool:
        """Step 3: Scrape championship finals times (ACC and NCAA)"""
        self.print_step(3, 5, "Scraping Championship Finals Times")
        
        # Define championship meets
        championships = [
            {
                "name": "ACC Championships 2025",
                "meet_id": "307261",
                "num_events": 42,
                "type": "acc",
                "output": "acc_2025_finals_times.json"
            },
            {
                "name": "NCAA Men's Championships 2025",
                "meet_id": "296883",
                "num_events": 21,
                "type": "ncaa",
                "output": "M_ncaa_2025_finals_times.json"
            },
            {
                "name": "NCAA Women's Championships 2025",
                "meet_id": "296884",
                "num_events": 21,
                "type": "ncaa",
                "output": "W_ncaa_2025_finals_times.json"
            }
        ]
        
        for champ in championships:
            print(f"\n🏆 Scraping {champ['name']}...")
            
            # Check if file already exists
            output_file = self.base_dir / champ['output']
            if output_file.exists():
                print(f"⏭️  {champ['output']} already exists, skipping...")
                continue
            
            result = self.run_script(
                "scrape_finals_times.py",
                [champ['meet_id'], str(champ['num_events']), champ['type']]
            )
            
            if result != 0:
                print(f"❌ Failed to scrape {champ['name']}")
                return False
            
            # Rename output file if needed
            default_output = self.base_dir / f"meet_{champ['meet_id']}_finals_times.json"
            if default_output.exists() and default_output != output_file:
                default_output.rename(output_file)
                print(f"📝 Renamed to {champ['output']}")
            
            print(f"✅ Successfully scraped {champ['name']}")
            time.sleep(2)  # Brief pause between meets
        
        return True
    
    def step_4_run_analysis(self) -> bool:
        """Step 4: Run championship comparison analysis"""
        self.print_step(4, 5, "Running Championship Comparison Analysis")
        
        # Check that all required files exist
        required_files = [
            "*_swimmers.csv",
            "*_Events/all_*_Events.json",
            "acc_2025_finals_times.json",
            "*_ncaa_2025_finals_times.json"
        ]
        
        if not self.check_files_exist(required_files):
            print("❌ Missing required input files for analysis")
            return False
        
        print("\n🔍 Running enhanced championship comparison...")
        
        args = []
        if self.gender:
            args.append(self.gender)
        
        result = self.run_script("champ_roster.py", args)
        
        if result != 0:
            print("❌ Analysis failed")
            return False
        
        print("✅ Successfully completed championship analysis")
        
        # Post-processing: Add NCAA cut times to generated CSVs
        print("\n📝 Post-processing: Adding NCAA cut times...")
        
        # Add to all generated CSVs regardless of gender filter
        csv_files = list(self.base_dir.glob("swimmer_championship_comparison*.csv"))
        
        for csv_file in csv_files:
            filename = csv_file.name
            
            # Determine gender from filename
            if "women" in filename.lower() or "_f" in filename.lower():
                self.add_ncaa_cut_times_to_csv(filename, "women")
            elif "men" in filename.lower() or "_m" in filename.lower():
                self.add_ncaa_cut_times_to_csv(filename, "men")
            else:
                # For combined CSV without gender in name, process both genders
                # We'll need to detect gender from swimmer_id by checking which CSV they came from
                self.add_ncaa_cut_times_to_csv(filename, "both")
        
        return True
    
    def step_5_summary(self) -> bool:
        """Step 5: Print summary of generated files"""
        self.print_step(5, 5, "Analysis Complete - Summary")
        
        # List generated CSV files
        print("📊 Generated Analysis Files:\n")
        
        csv_files = list(self.base_dir.glob("swimmer_championship_comparison*.csv"))
        
        if not csv_files:
            print("❌ No output CSV files found!")
            return False
        
        for csv_file in sorted(csv_files):
            file_size = csv_file.stat().st_size
            print(f"  ✓ {csv_file.name} ({file_size:,} bytes)")
        
        print(f"\n{'='*70}")
        print("🎉 WORKFLOW COMPLETE!")
        print(f"{'='*70}\n")
        print("Next Steps:")
        print("  1. Open the CSV files in Excel or your preferred spreadsheet software")
        print("  2. Review swimmer times and championship standards")
        print("  3. Identify swimmers who meet championship qualifying times")
        print("  4. Plan training focus based on time drops needed\n")
        
        return True
    
    def run(self) -> bool:
        """Execute the complete workflow"""
        print(f"\n{'*'*70}")
        print(f"CHAMPIONSHIP ANALYSIS WORKFLOW")
        print(f"{'*'*70}")
        print(f"Team ID: {self.team_id}")
        print(f"Gender: {self.gender.title() if self.gender else 'Both'}")
        print(f"{'*'*70}\n")
        
        steps = [
            self.step_1_scrape_swimmer_ids,
            self.step_2_scrape_swimmer_events,
            self.step_3_scrape_finals_times,
            self.step_4_run_analysis,
            self.step_5_summary
        ]
        
        for step_func in steps:
            if not step_func():
                print(f"\n❌ Workflow failed at {step_func.__name__}")
                return False
            time.sleep(1)  # Brief pause between steps
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Automated Championship Analysis Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --team 405 --gender women
  %(prog)s --team 405 --gender men
  %(prog)s --team 405
        """
    )
    
    parser.add_argument(
        "--team",
        type=str,
        required=True,
        help="Team ID from SwimCloud (e.g., 405 for Pitt)"
    )
    
    parser.add_argument(
        "--gender",
        type=str,
        choices=["men", "women", "male", "female", "m", "f"],
        help="Gender to analyze (men/women). If omitted, analyzes both."
    )
    
    parser.add_argument(
        "--skip-scraping",
        action="store_true",
        help="Skip scraping steps if data already exists"
    )
    
    args = parser.parse_args()
    
    # Normalize gender
    gender = None
    if args.gender:
        if args.gender.lower() in ["women", "female", "f"]:
            gender = "women"
        elif args.gender.lower() in ["men", "male", "m"]:
            gender = "men"
    
    # Create and run workflow
    workflow = ChampionshipWorkflow(args.team, gender)
    
    try:
        success = workflow.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
