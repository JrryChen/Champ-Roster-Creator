"""Scrape swimmer events and meet data from SwimCloud profiles"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import re
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime


def scrape_swimmer_profile(swimmer_id: str, swimmer_name: str = None) -> Optional[Dict]:
    """
    Scrape swimmer profile including events and meet data
    
    Args:
        swimmer_id: The swimmer's ID on SwimCloud
        swimmer_name: The swimmer's name (optional, from CSV)
        
    Returns:
        Dictionary with swimmer info and meet data, or None if error
    """
    url = f"https://www.swimcloud.com/swimmer/{swimmer_id}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching profile for swimmer {swimmer_id}: {e}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Use provided name or try to get from website
    if not swimmer_name:
        name_element = soup.find('h1', class_='swimmer-name')
        swimmer_name = name_element.get_text(strip=True) if name_element else "Unknown"
    
    print(f"Scraping profile for {swimmer_name} ({swimmer_id})")
    
    # Extract individual events
    individual_events = scrape_individual_events(soup)
    
    # Extract relay events
    relay_events = scrape_relay_events(soup)
    
    # Extract meet data from first meet
    meet_data = scrape_first_meet_data(soup)
    
    return {
        "swimmer": swimmer_name,
        "swimmer_id": swimmer_id,
        "individual_events": individual_events,
        "relay_events": relay_events,
        "first_meet": meet_data
    }


def scrape_individual_events(soup: BeautifulSoup) -> List[str]:
    """Extract individual events from swimmer profile"""
    events = []
    
    # Look for event links in the profile
    event_section = soup.find('div', class_='events')
    if not event_section:
        event_section = soup.find('section', class_=re.compile(r'event'))
    
    if event_section:
        event_links = event_section.find_all('a', href=re.compile(r'event='))
        for link in event_links:
            event_text = link.get_text(strip=True)
            if event_text and 'relay' not in event_text.lower():
                events.append(event_text)
    
    # Alternative: look for event data in tables
    if not events:
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if cells:
                    event_name = cells[0].get_text(strip=True)
                    # Check if it's not a relay (relay events typically have 4x in name)
                    if event_name and '4x' not in event_name and 'relay' not in event_name.lower():
                        if event_name not in events:
                            events.append(event_name)
    
    # Remove duplicates and clean up Finals/Prelims/Timed
    events = list(set(events))
    cleaned_events = []
    for event in events:
        # Remove "Finals", "Prelims", and "Timed"
        cleaned = event.replace("Finals", "").replace("Prelims", "").replace("Timed", "").strip()
        if cleaned not in cleaned_events:
            cleaned_events.append(cleaned)
    
    return cleaned_events


def scrape_relay_events(soup: BeautifulSoup) -> List[str]:
    """Extract relay events from swimmer profile"""
    relays = []
    
    # Look for relay events
    event_section = soup.find('div', class_='events')
    if not event_section:
        event_section = soup.find('section', class_=re.compile(r'event'))
    
    if event_section:
        relay_links = event_section.find_all('a', href=re.compile(r'event='))
        for link in relay_links:
            event_text = link.get_text(strip=True)
            if 'relay' in event_text.lower() or '4x' in event_text:
                relays.append(event_text)
    
    # Alternative: look for relay in tables
    if not relays:
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if cells:
                    event_name = cells[0].get_text(strip=True)
                    if '4x' in event_name or 'relay' in event_name.lower():
                        if event_name not in relays:
                            relays.append(event_name)
    
    # Remove duplicates and clean up - remove everything after "Relay"
    relays = list(set(relays))
    cleaned_relays = []
    for relay in relays:
        # Remove everything after and including the space after "Relay"
        # e.g., "400 Free Relay (Leadoff)Timed Finals" -> "400 Free Relay"
        cleaned = relay.split("Relay")[0] + "Relay" if "Relay" in relay else relay
        if cleaned not in cleaned_relays:
            cleaned_relays.append(cleaned)
    
    return cleaned_relays


def scrape_first_meet_data(soup: BeautifulSoup) -> Optional[Dict]:
    """Scrape data from the first meet on swimmer's profile"""
    
    # Look for meet results section
    meet_section = soup.find('div', class_=re.compile(r'meet|result'))
    
    if not meet_section:
        # Try to find meets in tables
        tables = soup.find_all('table')
        if tables:
            meet_section = tables[0]  # First table likely has meet data
    
    if not meet_section:
        print("  No meet data found on profile")
        return None
    
    meet_info = {}
    
    # Try to extract meet name
    meet_link = meet_section.find('a', href=re.compile(r'/meet/'))
    if meet_link:
        meet_info['meet_name'] = meet_link.get_text(strip=True)
        meet_id_match = re.search(r'/meet/(\d+)', meet_link.get('href', ''))
        if meet_id_match:
            meet_info['meet_id'] = meet_id_match.group(1)
    
    # Extract results from meet
    results = []
    rows = meet_section.find_all('tr')
    
    for row in rows[1:]:  # Skip header row
        cells = row.find_all('td')
        if len(cells) >= 3:
            event = cells[0].get_text(strip=True)
            time = cells[1].get_text(strip=True)
            place = cells[2].get_text(strip=True) if len(cells) > 2 else None
            
            if event and time:
                results.append({
                    "event": event,
                    "time": time,
                    "place": place
                })
    
    if results:
        meet_info['results'] = results
    
    return meet_info if meet_info else None


def load_swimmer_ids_from_csv(filename: str = "swimmers.csv") -> List[Tuple[str, str]]:
    """Load swimmer names and IDs from CSV file"""
    swimmers = []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'Swimmer ID' in row and 'Name' in row:
                    swimmers.append((row['Name'], row['Swimmer ID']))
    except FileNotFoundError:
        print(f"File {filename} not found")
    
    return swimmers


def scrape_swimmer_from_id(swimmer_id: str, swimmer_name: str = None) -> Optional[Dict]:
    """Scrape a single swimmer's profile and create JSON"""
    profile_data = scrape_swimmer_profile(swimmer_id, swimmer_name)
    
    if profile_data:
        print(f"  Individual events: {profile_data['individual_events']}")
        print(f"  Relay events: {profile_data['relay_events']}")
        if profile_data['first_meet']:
            print(f"  First meet: {profile_data['first_meet'].get('meet_name', 'Unknown')}")
            print(f"  Results: {len(profile_data['first_meet'].get('results', []))} events")
    
    return profile_data


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] not in ["M", "F"]:
        # Scrape specific swimmer by ID
        swimmer_id = sys.argv[1]
        swimmer_name = sys.argv[2] if len(sys.argv) > 2 else None
        print(f"Scraping swimmer {swimmer_id}...\n")
        
        data = scrape_swimmer_from_id(swimmer_id, swimmer_name)
        
        if data:
            # Save to JSON
            output_file = f"swimmer_{swimmer_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\nSaved to {output_file}")
            print("\nJSON Output:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        # Determine which CSV file to process
        if len(sys.argv) > 1 and sys.argv[1] == "F":
            csv_file = "F_swimmers.csv"
            output_dir = "F_Events"
        else:
            csv_file = "M_swimmers.csv"
            output_dir = "M_Events"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}\n")
        
        swimmers = load_swimmer_ids_from_csv(csv_file)
        
        if swimmers:
            all_data = []
            
            print(f"{'='*60}")
            print(f"Processing {csv_file}")
            print(f"{'='*60}")
            
            for name, swimmer_id in swimmers:
                print(f"\n{'-'*60}")
                data = scrape_swimmer_from_id(swimmer_id, name)
                
                if data:
                    all_data.append(data)
                    
                    # Save individual swimmer JSON to output folder
                    output_file = os.path.join(output_dir, f"{name.replace(' ', '_')}_{swimmer_id}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"  Saved to {output_file}")
            
            # Save combined JSON to output folder
            if all_data:
                combined_file = os.path.join(output_dir, f"all_{output_dir}.json")
                with open(combined_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, indent=2, ensure_ascii=False)
                
                print(f"\n{'='*60}")
                print(f"Saved {len(all_data)} swimmers to {combined_file}")
        else:
            print(f"No swimmers found in {csv_file}")
