import asyncio
import json
import sys
import os

# Add SwimScrape to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SwimScrape', 'src'))

from SwimScrape.src.clients import TopTimesClient
from SwimScrape.src.region_codes import region_code
from event_dictionary import acc_events, ncaa_events

# Event mappings: event_id -> (stroke, distance) for NCAA, (stroke, distance, gender) for ACC
ncaa_event_map = {
    1: (1, 200),   # 200 Medley Relay
    2: (2, 800),   # 800 Free Relay
    3: (2, 500),   # 500 Free
    4: (3, 200),   # 200 IM
    5: (2, 50),    # 50 Free
    7: (2, 200),   # 200 Free Relay
    8: (4, 100),   # 100 Fly
    9: (3, 400),   # 400 IM
    10: (2, 200),  # 200 Free
    11: (5, 100),  # 100 Breast
    12: (6, 100),  # 100 Back
    14: (1, 400),  # 400 Medley Relay
    15: (2, 1650), # 1650 Free
    16: (6, 200),  # 200 Back
    17: (2, 100),  # 100 Free
    18: (5, 200),  # 200 Breast
    19: (4, 200),  # 200 Fly
    21: (2, 400),  # 400 Free Relay
}

acc_event_map = {
    3: (1, 200, 'F'),   # 200 Medley Relay Women
    4: (1, 200, 'M'),   # 200 Medley Relay Men
    5: (2, 800, 'F'),   # 800 Free Relay Women
    6: (2, 800, 'M'),   # 800 Free Relay Men
    7: (2, 200, 'F'),   # 200 Free Relay Women
    8: (2, 200, 'M'),   # 200 Free Relay Men
    9: (2, 500, 'F'),   # 500 Free Women
    10: (2, 500, 'M'),  # 500 Free Men
    11: (3, 200, 'F'),  # 200 IM Women
    12: (3, 200, 'M'),  # 200 IM Men
    13: (2, 50, 'F'),   # 50 Free Women
    14: (2, 50, 'M'),   # 50 Free Men
    16: (3, 400, 'F'),  # 400 IM Women
    17: (3, 400, 'M'),  # 400 IM Men
    18: (4, 100, 'F'),  # 100 Fly Women
    19: (4, 100, 'M'),  # 100 Fly Men
    20: (2, 200, 'F'),  # 200 Free Women
    21: (2, 200, 'M'),  # 200 Free Men
    23: (4, 200, 'F'),  # 200 Fly Women
    24: (4, 200, 'M'),  # 200 Fly Men
    25: (6, 100, 'F'),  # 100 Back Women
    26: (6, 100, 'M'),  # 100 Back Men
    27: (5, 100, 'F'),  # 100 Breast Women
    28: (5, 100, 'M'),  # 100 Breast Men
    30: (1, 400, 'F'),  # 400 Medley Relay Women
    31: (1, 400, 'M'),  # 400 Medley Relay Men
    32: (2, 1650, 'F'), # 1650 Free Women
    33: (2, 1650, 'M'), # 1650 Free Men
    34: (6, 200, 'F'),  # 200 Back Women
    35: (6, 200, 'M'),  # 200 Back Men
    36: (2, 100, 'F'),  # 100 Free Women
    37: (2, 100, 'M'),  # 100 Free Men
    38: (5, 200, 'F'),  # 200 Breast Women
    39: (5, 200, 'M'),  # 200 Breast Men
    41: (2, 400, 'F'),  # 400 Free Relay Women
    42: (2, 400, 'M'),  # 400 Free Relay Men
}

async def scrape_top_times():
    client = TopTimesClient()

    regions = {
        'ncaa': 'division_1',
        'acc': 'conference_3'
    }

    for region_name, region_code_val in regions.items():
        print(f"Scraping {region_name.upper()}...")

        if region_name == 'ncaa':
            event_map = ncaa_event_map
            genders = ['M', 'F']
            event_names = ncaa_events
        else:
            event_map = acc_event_map
            genders = [None]  # gender included in map
            event_names = acc_events

        all_data = {}

        for event_id, event_info in event_map.items():
            if region_name == 'ncaa':
                stroke, distance = event_info
                for gender in genders:
                    gender_code = 1 if gender == 'M' else 2
                    event_code = f"{stroke}|{distance}|{gender_code}"
                    event_key = f"{event_names[event_id]} {gender}"
            else:
                stroke, distance, gender = event_info
                gender_code = 1 if gender == 'M' else 2
                event_code = f"{stroke}|{distance}|{gender_code}"
                event_key = event_names[event_id]

            print(f"  Scraping {event_key}...")

            try:
                # Fetch multiple pages to get ~100 times
                times = await client.fetch_multiple_pages(
                    event=event_code,
                    gender='M' if gender_code == 1 else 'F',
                    num_pages=5,  # Assuming ~20-25 per page, 5 pages = ~100-125
                    region=region_code_val,
                    season_id="29",  # 2024-25 season
                    eventcourse="Y"
                )

                # Take top 100
                top_times = times[:100]

                # Convert to dict
                times_dict = []
                for time in top_times:
                    d = {
                        'event': time.event,
                        'time': time.time,
                        'athlete_name': time.participant.name if hasattr(time.participant, 'name') else str(time.participant),
                        'team_name': time.participant.team.name if hasattr(time.participant, 'team') and time.participant.team else 'Unknown',
                        'is_relay': time.is_relay,
                        'date': time.date.isoformat() if time.date else None,
                        'meet': time.meet,
                        'pool': time.pool,
                        'rank': time.rank,
                        'points': time.points,
                        'fina_points': time.fina_points,
                    }
                    times_dict.append(d)

                all_data[event_key] = times_dict
                print(f"    Got {len(times_dict)} times")

            except Exception as e:
                print(f"    Error scraping {event_key}: {e}")
                all_data[event_key] = []

        # Save to file
        filename = f"{region_name}_top_100_times_2025.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        print(f"Saved {region_name.upper()} data to {filename}")

if __name__ == "__main__":
    asyncio.run(scrape_top_times())