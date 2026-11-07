"""Scrape finals placement times from SwimCloud meet events"""

import requests
from bs4 import BeautifulSoup
import json
import re
import sys
from typing import Dict, List, Optional
from event_dictionary import acc_events, ncaa_events


def scrape_event_times(meet_id: str, event_num: int, event_dict: Dict = None) -> Optional[Dict]:
    """
    Scrape placement times for a specific event
    
    Args:
        meet_id: The meet ID on SwimCloud
        event_num: The event number
        event_dict: Dictionary mapping event numbers to names (default: acc_events)
        
    Returns:
        Dictionary with event info and placement times
    """
    if event_dict is None:
        event_dict = acc_events
    url = f"https://www.swimcloud.com/results/{meet_id}/event/{event_num}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching event {event_num}: {e}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Get event name from dictionary
    event_name = event_dict.get(event_num, f"Event {event_num}")
    
    print(f"Scraping: Event {event_num} - {event_name}")
    
    # Determine if this is a relay or individual event
    is_relay = "relay" in event_name.lower() or "4x" in event_name.lower()
    
    # Look for prelims or finals sections
    prelims_caption = soup.find('caption', id=lambda x: x and 'round-PRE' in x)
    finals_caption = soup.find('caption', id=lambda x: x and 'round-FIN' in x)
    
    # Get time links - prefer prelims if available, else finals
    time_links = []
    is_timed_finals = False
    
    if prelims_caption:
        # Get all time links after the prelims caption
        table = prelims_caption.find_parent('table')
        if table:
            time_links = table.find_all('a', href=lambda x: x and '/times/' in x)
    elif finals_caption:
        # Get all time links after the finals caption
        table = finals_caption.find_parent('table')
        if table:
            time_links = table.find_all('a', href=lambda x: x and '/times/' in x)
            is_timed_finals = True
    else:
        # Fall back to all time links on the page
        time_links = soup.find_all('a', href=lambda x: x and '/times/' in x)
        # Check if event name indicates timed finals
        is_timed_finals = "timed final" in event_name.lower()
    
    if not time_links:
        # Skip events with no times (likely diving/other non-timed events)
        return None
    
    # Extract times and their positions
    times_data = []
    for link in time_links:
        time_text = link.get_text(strip=True)
        # Verify it looks like a time
        if re.match(r'\d+:?\d+\.\d+', time_text):
            times_data.append(time_text)
    
    if not times_data:
        return None
    
    # Determine placement positions based on event type
    if is_timed_finals or is_relay:
        # For timed finals/relays: get 1st, 3rd, 8th
        target_places = [1, 3, 8]
    else:
        # For prelims: get 1st, 3rd, 8th, 16th, 24th
        target_places = [1, 3, 8, 16, 24]
    
    # Map times to placements (first time = 1st, etc.)
    placements = {}
    for i, place in enumerate(range(1, len(times_data) + 1)):
        if place in target_places:
            placements[place] = times_data[i]
            print(f"  {place}{get_ordinal_suffix(place)} place: {times_data[i]}")
    
    if not placements:
        print(f"  No placement times found")
        return None
    
    return {
        "event_number": event_num,
        "event_name": event_name,
        "placements": placements
    }


def get_ordinal_suffix(n: int) -> str:
    """Get ordinal suffix for a number (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return suffix


def scrape_all_meet_events(meet_id: str, num_events: int = 42, event_dict: Dict = None) -> List[Dict]:
    """
    Scrape placement times for all events in a meet
    
    Args:
        meet_id: The meet ID on SwimCloud
        num_events: Number of events to scrape (default 42)
        event_dict: Dictionary mapping event numbers to names (default: acc_events)
        
    Returns:
        List of event dictionaries with placement times
    """
    if event_dict is None:
        event_dict = acc_events
    
    all_events = []
    
    print(f"Scraping meet {meet_id} - {num_events} events")
    print("="*60)
    
    for event_num in range(1, num_events + 1):
        print(f"\nEvent {event_num}:")
        event_data = scrape_event_times(meet_id, event_num, event_dict)
        
        if event_data:
            all_events.append(event_data)
    
    return all_events


if __name__ == "__main__":
    # Default meet ID from the example
    meet_id = "307261"
    num_events = 42
    event_type = "acc"  # "acc" or "ncaa"
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        meet_id = sys.argv[1]
    if len(sys.argv) > 2:
        num_events = int(sys.argv[2])
    if len(sys.argv) > 3:
        event_type = sys.argv[3].lower()
    
    # Select the appropriate event dictionary
    event_dict = ncaa_events if event_type == "ncaa" else acc_events
    
    print(f"Starting scrape of meet {meet_id} ({event_type.upper()})\n")
    
    # Scrape all events
    events_data = scrape_all_meet_events(meet_id, num_events, event_dict)
    
    if events_data:
        # Save to JSON
        output_file = f"meet_{meet_id}_finals_times.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"Scraped {len(events_data)} events")
        print(f"Saved to {output_file}")
        
        # Print summary
        print(f"\nSummary:")
        for event in events_data:
            print(f"  Event {event['event_number']}: {event['event_name']}")
            print(f"    Placements: {list(event['placements'].keys())}")
    else:
        print("No event data found")
