"""
Compare swimmer times to championship standards
Fetch swimmer best times, current season times, and rankings
Compare to ACC and NCAA finals standards with TopTimes integration
"""

import csv
import json
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
import re
import time

# Add SwimScrape to path
sys.path.insert(0, str(Path(__file__).parent / "SwimScrape"))

from SwimScrape.src.clients import IndividualFastestTimesClient, SeasonalTimesClient, TopTimesClient
from SwimScrape.src.models import SwimTime

# Import NCAA invite times
from ncaa_invite_times import w_invite_2025_codes, m_invite_2025_codes


def parse_time_to_seconds(time_str: str) -> Optional[float]:
    """Convert time string (MM:SS.xx or SS.xx) to seconds"""
    if not time_str or not isinstance(time_str, str):
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


def seconds_to_time_string(seconds: float) -> str:
    """Convert seconds back to MM:SS.xx or SS.xx format"""
    if seconds < 60:
        return f"{seconds:.2f}"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:06.2f}"


def parse_event_name(event_name: str) -> Tuple[int, str, str]:
    """
    Parse event name to extract distance, stroke, gender
    Examples: "100 Free Women" -> (100, "Free", "Women"), "100 Y Free" -> (100, "Free", "")
    """
    # Remove extra spaces and normalize
    event_name = ' '.join(event_name.split())
    
    # Remove "Y" or "S" for yards/short course if present
    event_name = re.sub(r'\s+[YS]\s+', ' ', event_name)
    
    # Try pattern with explicit gender: number + stroke + gender
    match = re.match(r'(\d+)\s+(\w+)\s+(Women|Men|Mixed)', event_name, re.IGNORECASE)
    if match:
        distance = int(match.group(1))
        stroke = match.group(2)
        gender = match.group(3)
        return distance, stroke, gender
    
    # Try pattern without gender: just number + stroke
    match = re.match(r'(\d+)\s+(\w+)', event_name, re.IGNORECASE)
    if match:
        distance = int(match.group(1))
        stroke = match.group(2)
        # We'll infer gender from context later
        return distance, stroke, ""
    
    return None, None, None


def load_swimmer_csv(csv_path: str) -> List[Dict]:
    """Load swimmer CSV and return list of swimmer dicts"""
    swimmers = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Name'] and row['Swimmer ID']:
                    swimmers.append({
                        'name': row['Name'].strip(),
                        'swimmer_id': row['Swimmer ID'].strip()
                    })
    except Exception as e:
        print(f"Error loading CSV {csv_path}: {e}")
    
    return swimmers


def load_events_json(json_path: str) -> Dict[str, Dict]:
    """Load events JSON and return dict of swimmer events"""
    swimmers_dict = {}
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for swimmer in data:
                swimmer_id = swimmer.get('swimmer_id')
                if swimmer_id:
                    swimmers_dict[swimmer_id] = {
                        'name': swimmer.get('swimmer'),
                        'individual_events': swimmer.get('individual_events', []),
                        'relay_events': swimmer.get('relay_events', [])
                    }
    except Exception as e:
        print(f"Error loading JSON {json_path}: {e}")
    
    return swimmers_dict


def load_finals_times(json_path: str) -> Dict[str, Dict]:
    """Load finals times JSON and return dict of event_number -> event data"""
    finals = {}
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for event in data:
                event_num = event.get('event_number')
                event_name = event.get('event_name')
                placements = event.get('placements', {})
                
                # Convert placement strings to dicts with seconds and time string
                placement_data = {}
                for place_str, time_str in placements.items():
                    seconds = parse_time_to_seconds(time_str)
                    placement_data[int(place_str)] = {
                        'time_str': time_str,
                        'seconds': seconds
                    }
                
                finals[event_name.lower()] = {
                    'event_number': event_num,
                    'event_name': event_name,
                    'placements': placement_data
                }
    except Exception as e:
        print(f"Error loading finals times {json_path}: {e}")
    
    return finals


async def get_swimmer_season_best(swimmer_id: str, stroke_code: str, distance: int, gender: str, retry_count: int = 0) -> Optional[str]:
    """Fetch swimmer's current season best time with exponential backoff"""
    try:
        gender_code = "M" if gender in ["Men", "M"] else "F"
        event_code = f"{stroke_code}|{distance}|{gender_code}"
        
        client = SeasonalTimesClient(swimmer_id, timeout=10)
        times = await client.fetch_times_by_event(event_code, course="Y")
        
        if times:
            # Return fastest time this season (first one is usually fastest)
            return times[0].time
        
        return None
    except Exception as e:
        # Retry with exponential backoff for rate limit errors
        print(e)
        if "429" in str(e) or "403" in str(e) and retry_count < 5:
            wait_time = 60
            print(f"    Rate limited. Waiting {wait_time}s before retry...")
            await asyncio.sleep(wait_time)
            return await get_swimmer_season_best(swimmer_id, stroke_code, distance, gender, retry_count + 1)
        return None


async def fetch_top_times(event_code: str, gender: str, placement: int, retry_count: int = 0) -> Optional[float]:
    """
    Fetch top times from ACC/NCAA with exponential backoff
    Returns the time in seconds for a specific placement
    """
    try:
        client = TopTimesClient(timeout=10)
        race = await client.fetch_times(
            event=event_code,
            gender=gender,
            region="division_1",
            season_id="29",
            page=1,
            eventcourse="Y"
        )
        
        if race.times and len(race.times) > placement - 1:
            time_str = race.times[placement - 1].time
            return parse_time_to_seconds(time_str)
        
        return None
    except Exception as e:
        # Retry with exponential backoff for rate limit errors
        if "429" in str(e) and retry_count < 3:
            wait_time = (2 ** retry_count) * 5  # 5s, 10s, 20s
            await asyncio.sleep(wait_time)
            return await fetch_top_times(event_code, gender, placement, retry_count + 1)
        return None


def get_invite_standard(event_code: str, gender: str) -> Optional[float]:
    """Get NCAA invite standard for an event"""
    if gender in ["Women", "F"]:
        return w_invite_2025_codes.get(event_code)
    else:
        return m_invite_2025_codes.get(event_code)


async def process_swimmer(swimmer: Dict, events_dict: Dict, acc_finals: Dict, ncaa_finals: Dict, gender: str) -> Tuple[List[Dict], List[Dict], Set[str]]:
    """
    Process a single swimmer and return comparison rows for both ACC and NCAA
    Returns (acc_results, ncaa_results, swimmers_for_ncaa_list)
    """
    swimmer_id = swimmer['swimmer_id']
    swimmer_name = swimmer['name']
    
    acc_results = []
    ncaa_results = []
    swimmers_for_ncaa = set()
    
    print(f"Processing {swimmer_name} ({swimmer_id})...")
    
    # Get swimmer's individual events from JSON
    if swimmer_id not in events_dict:
        print(f"  No events found in JSON")
        return acc_results, ncaa_results, swimmers_for_ncaa
    
    swimmer_events = events_dict[swimmer_id]
    individual_events = swimmer_events.get('individual_events', [])
    
    if not individual_events:
        print(f"  No individual events listed")
        return acc_results, ncaa_results, swimmers_for_ncaa
    
    # Parse event names from JSON
    target_events = {}  # Map of distance+stroke to event name
    for event_name in individual_events:
        distance, stroke, _ = parse_event_name(event_name)
        if distance and stroke:
            key = f"{distance}_{stroke}".lower()
            target_events[key] = f"{distance} {stroke}"
    
    if not target_events:
        print(f"  Could not parse individual events")
        return acc_results, ncaa_results, swimmers_for_ncaa
    
    # Fetch all best times for this swimmer with retry logic
    all_times = None
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries and all_times is None:
        try:
            client = IndividualFastestTimesClient(swimmer_id, timeout=10)
            all_times = await client.fetch_best_times()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = (2 ** retry_count) * 8  # 8s, 16s, 32s
                    print(f"  Rate limited. Waiting {wait_time}s before retry {retry_count}...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"  Max retries exceeded for rate limiting")
                    return acc_results, ncaa_results, swimmers_for_ncaa
            else:
                print(f"  Error fetching times: {e}")
                return acc_results, ncaa_results, swimmers_for_ncaa
    
    if not all_times:
        print(f"  No times found")
        return acc_results, ncaa_results, swimmers_for_ncaa
    
    # Track processed events to avoid duplicates
    processed = set()
    
    for swim_time in all_times:
        if not swim_time.time:
            continue
        
        # Parse event code (stroke|distance|gender)
        event_parts = swim_time.event.split('|')
        if len(event_parts) < 3:
            continue
        
        stroke_code = event_parts[0]
        distance = int(event_parts[1])
        event_gender = event_parts[2]
        
        # Get stroke name
        stroke_names = {'1': 'Free', '2': 'Back', '3': 'Breast', '4': 'Fly', '5': 'IM'}
        stroke = stroke_names.get(stroke_code, f"Stroke{stroke_code}")
        
        # Create event key
        event_key = f"{distance}_{stroke}".lower()
        
        # Skip if this event is not in their individual events list
        if event_key not in target_events:
            continue
        
        # Check if we've already processed this event
        event_id = f"{swimmer_id}_{stroke_code}_{distance}"
        if event_id in processed:
            continue
        processed.add(event_id)
        
        # Fetch season best with rate limit handling
        season_best_time = await get_swimmer_season_best(swimmer_id, stroke_code, distance, gender, retry_count=0)
        print("Season Best", season_best_time)
        # Look for matching championship standards
        event_display = f"{distance} {stroke}".lower()
        acc_with_gender = f"{distance} {stroke} {gender}".lower()
        acc_data = acc_finals.get(acc_with_gender) or acc_finals.get(event_display)
        
        # NCAA finals don't have gender in name, just event
        ncaa_data = ncaa_finals.get(event_display)
        
        if not acc_data and not ncaa_data:
            continue
        
        swim_seconds = parse_time_to_seconds(swim_time.time)
        season_seconds = parse_time_to_seconds(season_best_time) if season_best_time else None
        
        if not swim_seconds:
            continue
        
        # Format times for CSV output
        best_time_formatted = seconds_to_time_string(swim_seconds)
        season_best_formatted = seconds_to_time_string(season_seconds) if season_seconds else 'N/A'
        
        # Build base row data
        base_row = {
            'swimmer_name': swimmer_name,
            'swimmer_id': swimmer_id,
            'event': f"{distance} {stroke}",
            'best_time': best_time_formatted,
            'season_best': season_best_formatted,
        }
        
        event_code = f"{stroke_code}|{distance}|{event_gender}"
        gender_code = "M" if gender in ["Men", "M"] else "F"
        
        # Process ACC comparisons
        if acc_data:
            acc_row = base_row.copy()
            placements = sorted(acc_data['placements'].keys())
            
            # Add columns for each placement
            for place in placements:
                placement_data = acc_data['placements'][place]
                standard_seconds = placement_data['seconds']
                
                if standard_seconds:
                    diff_seconds = swim_seconds - standard_seconds
                    
                    # If faster than standard, show 0, otherwise show time difference
                    if diff_seconds < 0:
                        acc_row[f'time_drop_to_{place}'] = 0
                    else:
                        acc_row[f'time_drop_to_{place}'] = diff_seconds
            
            acc_results.append(acc_row)
            
            # Check if meets NCAA invite standard
            invite_standard = get_invite_standard(event_code, gender_code)
            if invite_standard and swim_seconds <= invite_standard:
                swimmers_for_ncaa.add(f"{swimmer_id}_{event_id}")
        
        # Process NCAA comparisons
        if ncaa_data:
            ncaa_row = base_row.copy()
            placements = sorted(ncaa_data['placements'].keys())
            
            # Add columns for each placement
            for place in placements:
                placement_data = ncaa_data['placements'][place]
                standard_seconds = placement_data['seconds']
                
                if standard_seconds:
                    diff_seconds = swim_seconds - standard_seconds
                    
                    # If faster than standard, show 0, otherwise show time difference
                    if diff_seconds < 0:
                        ncaa_row[f'time_drop_to_{place}'] = 0
                    else:
                        ncaa_row[f'time_drop_to_{place}'] = diff_seconds
            
            ncaa_results.append(ncaa_row)
        
        await asyncio.sleep(2)  # Increased rate limiting between events
    
    return acc_results, ncaa_results, swimmers_for_ncaa


def get_all_column_names(results: List[Dict]) -> List[str]:
    """Extract all unique column names from results, ordered properly"""
    if not results:
        return []
    
    # Start with base columns in order
    base_columns = ['swimmer_name', 'swimmer_id', 'event', 'best_time', 'season_best']
    
    # Find all placement columns
    placement_columns = set()
    for row in results:
        for col in row.keys():
            if col.startswith('time_drop_to_'):
                placement_columns.add(col)
    
    # Sort placement columns numerically
    placement_columns = sorted(placement_columns, 
                               key=lambda x: int(x.replace('time_drop_to_', '')))
    
    return base_columns + placement_columns


async def main():
    """Main function to process all swimmers and generate comparison CSVs"""
    
    # Load CSVs and JSONs
    print("Loading data files...")
    gender_filter = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        if arg in {"men", "male"}:
            gender_filter = "men"
        elif arg in {"women", "female", "women_only", "f"}:
            gender_filter = "women"
    
    m_swimmers = load_swimmer_csv("M_swimmers.csv")
    f_swimmers = load_swimmer_csv("F_swimmers.csv")
    
    m_events = load_events_json("M_Events/all_M_Events.json")
    f_events = load_events_json("F_Events/all_F_Events.json")
    
    acc_finals = load_finals_times("acc_2025_finals_times.json")
    m_ncaa_finals = load_finals_times("M_ncaa_2025_finals_times.json")
    w_ncaa_finals = load_finals_times("W_ncaa_2025_finals_times.json")
    
    print(f"Loaded {len(m_swimmers)} male swimmers and {len(f_swimmers)} female swimmers")
    
    # Process swimmers
    all_acc_results = []
    all_ncaa_results = []
    swimmers_for_ncaa = set()
    
    if gender_filter in (None, "men"):
        print("\n=== PROCESSING MALE SWIMMERS ===")
        for i, swimmer in enumerate(m_swimmers):
            acc_rows, ncaa_rows, ncaa_set = await process_swimmer(
                swimmer, m_events, acc_finals, m_ncaa_finals, "Men"
            )
            all_acc_results.extend(acc_rows)
            all_ncaa_results.extend(ncaa_rows)
            swimmers_for_ncaa.update(ncaa_set)
            # Longer delay between swimmers to avoid rate limiting
            await asyncio.sleep(3)
            if (i + 1) % 5 == 0:
                print(f"  Processed {i + 1}/{len(m_swimmers)} swimmers. Pausing for 60s...")
                await asyncio.sleep(60)
    
    if gender_filter in (None, "women"):
        print("\n=== PROCESSING FEMALE SWIMMERS ===")
        for i, swimmer in enumerate(f_swimmers):
            acc_rows, ncaa_rows, ncaa_set = await process_swimmer(
                swimmer, f_events, acc_finals, w_ncaa_finals, "Women"
            )
            all_acc_results.extend(acc_rows)
            all_ncaa_results.extend(ncaa_rows)
            swimmers_for_ncaa.update(ncaa_set)
            # Longer delay between swimmers to avoid rate limiting
            await asyncio.sleep(3)
            if (i + 1) % 5 == 0:
                print(f"  Processed {i + 1}/{len(f_swimmers)} swimmers. Pausing for 60s...")
                await asyncio.sleep(60)
    
    # Write ACC results to CSV
    if all_acc_results:
        acc_output_file = "swimmer_championship_comparison_acc.csv"
        if gender_filter == "women":
            acc_output_file = "swimmer_championship_comparison_acc_women.csv"
        elif gender_filter == "men":
            acc_output_file = "swimmer_championship_comparison_acc_men.csv"
        
        acc_columns = get_all_column_names(all_acc_results)
        
        with open(acc_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=acc_columns, restval='')
            writer.writeheader()
            writer.writerows(all_acc_results)
        
        print(f"\n✅ ACC output written to {acc_output_file}")
        print(f"ACC total rows: {len(all_acc_results)}")
    else:
        print("❌ No ACC comparison data generated")
    
    # Write NCAA results to CSV (includes swimmers who meet invite standard)
    if all_ncaa_results:
        ncaa_output_file = "swimmer_championship_comparison_ncaa.csv"
        if gender_filter == "women":
            ncaa_output_file = "swimmer_championship_comparison_ncaa_women.csv"
        elif gender_filter == "men":
            ncaa_output_file = "swimmer_championship_comparison_ncaa_men.csv"
        
        ncaa_columns = get_all_column_names(all_ncaa_results)
        
        with open(ncaa_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ncaa_columns, restval='')
            writer.writeheader()
            writer.writerows(all_ncaa_results)
        
        print(f"\n✅ NCAA output written to {ncaa_output_file}")
        print(f"NCAA total rows: {len(all_ncaa_results)}")
        print(f"Swimmers qualifying for NCAA invite: {len(swimmers_for_ncaa)}")
    else:
        print("❌ No NCAA comparison data generated")


if __name__ == "__main__":
    asyncio.run(main())
