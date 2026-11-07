"""Compare all individual events from an events JSON against top times

Reads `M_Events/all_M_Events.json` (or a provided path) and for each swimmer
and each `individual_events` entry, fetches the top times (NCAA/ACC) and the
swimmer's seasonal best, then writes a CSV with the comparison per event.

Usage:
  python compare_all_events_from_json.py [--json M_Events/all_M_Events.json] [--out comparisons.csv] [--region division_1] [--season 29] [--pages 3]
"""
import argparse
import asyncio
import json
import re
import csv
import sys
from pathlib import Path
import os
import httpx

# Ensure package import works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SwimScrape'))
from SwimScrape.src.clients import TopTimesClient, SeasonalTimesClient


STROKE_TO_CODE = {
    'free': '1',
    'back': '2',
    'breast': '3',
    'fly': '4',
    'im': '5',
}


def parse_event_name(event_name: str):
    """Parse a human event name like '100 Y Fly' and return (distance, stroke)
    Returns (distance:int, stroke_str) or (None, None) if not parseable.
    """
    if not event_name or not isinstance(event_name, str):
        return None, None

    # Normalize
    s = event_name.strip()
    # Remove course letters (Y/L/S) and parentheses
    s = re.sub(r'[()\[\]]', ' ', s)
    s = re.sub(r'\b[YLS]\b', '', s, flags=re.IGNORECASE)
    s = s.replace('Timed Finals', '').replace('Finals', '').replace('Prelims', '')
    s = ' '.join(s.split())

    # Look for distance (digits or timelike 15:36.36) at start
    m = re.match(r'^(\d+)', s)
    if not m:
        # try to find leading minutes:seconds for long events like 15:36.36 -> treat as 1650 or skip
        return None, None
    distance = int(m.group(1))

    # Look for stroke word
    for stroke in ('free', 'fly', 'back', 'breast', 'im'):
        if re.search(rf'\b{stroke}\b', s, flags=re.IGNORECASE):
            return distance, stroke.lower()

    return None, None


def parse_time_to_seconds(time_str: str):
    if not time_str or not isinstance(time_str, str):
        return None
    time_str = time_str.strip()
    if ':' in time_str:
        parts = time_str.split(':')
        try:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        except Exception:
            return None
    try:
        return float(time_str)
    except Exception:
        return None


async def compare(json_path: Path, out_csv: Path, region: str, season: str, pages: int, gender: str = 'M'):
    if not json_path.exists():
        print(f"JSON not found: {json_path}")
        return 1

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rows = []

    top_client = TopTimesClient(timeout=15)
    # Cache top times per (event_code, region) to avoid duplicate requests
    top_times_cache: dict[tuple[str, str], list] = {}

    for swimmer in data:
        swimmer_name = swimmer.get('swimmer') or swimmer.get('name') or ''
        swimmer_id = str(swimmer.get('swimmer_id') or '')
        individual_events = swimmer.get('individual_events', []) or []

        if not swimmer_id or not individual_events:
            continue

        print(f"Processing {swimmer_name} ({swimmer_id}) with {len(individual_events)} events")

        # Parse individual events into structured list then sort by distance, then stroke code
        parsed_events = []
        for ev in individual_events:
            distance, stroke = parse_event_name(ev)
            if distance is None or stroke is None:
                print(f"  Skipping unparsable event '{ev}'")
                continue

            stroke_code = STROKE_TO_CODE.get(stroke)
            if not stroke_code:
                print(f"  Unsupported stroke '{stroke}' for event '{ev}'")
                continue

            # Build event codes (ACC uses region 'conference_3')
            gender_letter = (gender or 'M').upper()
            gender_num = '1' if gender_letter == 'M' else '2'
            event_for_top = f"{stroke_code}|{distance}|{gender_num}"
            event_for_season = f"{stroke_code}|{distance}|{gender_letter}"

            parsed_events.append({
                'original': ev,
                'distance': distance,
                'stroke': stroke,
                'stroke_code': int(stroke_code),
                'event_for_top': event_for_top,
                'event_for_season': event_for_season,
            })

        # sort by distance then stroke code so output order like: 50 Free, 100 Free, 100 Fly
        parsed_events.sort(key=lambda x: (x['distance'], x['stroke_code']))

        for ev_item in parsed_events:
            ev = ev_item['original']
            distance = ev_item['distance']
            stroke = ev_item['stroke']
            stroke_code = str(ev_item['stroke_code'])
            event_for_top = ev_item['event_for_top']
            event_for_season = ev_item['event_for_season']

            # Fetch top times (multiple pages) for both ACC (user region) and Division 1
            max_retries = 3

            def get_cached(region_key: str):
                return top_times_cache.get((event_for_top, region_key))

            async def fetch_top_for_region(region_key: str):
                cached = get_cached(region_key)
                if cached is not None:
                    return cached

                for attempt in range(max_retries):
                    try:
                        times = await top_client.fetch_multiple_pages(
                            event=event_for_top,
                            gender=gender_letter,
                            num_pages=pages,
                            region=region_key,
                            season_id=season,
                            eventcourse='Y'
                        )
                        top_times_cache[(event_for_top, region_key)] = times
                        return times
                    except Exception as e:
                        s = str(e)
                        if '403' in s or '429' in s:
                            print(f"  Received {s.split(':',1)[0]} for top times ({region_key}). Waiting 60s before retry (attempt {attempt+1}/{max_retries})...")
                            await asyncio.sleep(60)
                            continue
                        else:
                            print(f"  Error fetching top times for {ev} region {region_key}: {e}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2)
                                continue
                            top_times_cache[(event_for_top, region_key)] = []
                            return []

            # fetch ACC (user-provided region, likely conference_3) and NCAA Division 1
            acc_times = await fetch_top_for_region(region)
            ncaa_times = await fetch_top_for_region('division_1')

            # Determine swimmer's placement in each list (cap at 50)
            def norm_name(s: str) -> str:
                return ''.join(ch for ch in (s or '').lower() if ch.isalnum() or ch.isspace()).strip()

            swimmer_norm = norm_name(swimmer_name)

            def find_placement_in_list(times_list: list) -> object:
                placement_local = '50+'
                try:
                    for i, t in enumerate(times_list[:50]):
                        participant = getattr(t, 'participant', None)
                        athlete_id = None
                        participant_name = None
                        if participant:
                            athlete_id = getattr(participant, 'athlete_id', None) or getattr(participant, 'athleteId', None)
                            participant_name = getattr(participant, 'name', None)

                        if athlete_id and str(athlete_id) == swimmer_id:
                            return i + 1

                        if participant_name:
                            part_norm = norm_name(participant_name)
                            if swimmer_norm == part_norm:
                                return i + 1
                            sw_last = swimmer_norm.split()[-1] if swimmer_norm.split() else ''
                            part_last = part_norm.split()[-1] if part_norm.split() else ''
                            if sw_last and sw_last == part_last:
                                return i + 1
                except Exception:
                    return '50+'
                return placement_local

            acc_placement = find_placement_in_list(acc_times)
            ncaa_placement = find_placement_in_list(ncaa_times)

            # Fetch swimmer seasonal best for that event
            seasonal_client = SeasonalTimesClient(swimmer_id, timeout=10)
            # Fetch seasonal times with retries on 403/429
            s_times = []
            for attempt in range(max_retries):
                try:
                    s_times = await seasonal_client.fetch_times_by_event(event_for_season, course='Y')
                    break
                except Exception as e:
                    s = str(e)
                    if '403' in s or '429' in s:
                        print(f"  Received {s.split(':',1)[0]} for swimmer {swimmer_id}. Waiting 60s before retry (attempt {attempt+1}/{max_retries})...")
                        await asyncio.sleep(60)
                        continue
                    else:
                        print(f"  Error fetching seasonal times for swimmer {swimmer_id} event {ev}: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)
                            continue
                        s_times = []
                        break

            swimmer_best_raw = None
            if s_times:
                swimmer_best_raw = s_times[0].time

            rows.append({
                'swimmer_id': swimmer_id,
                'swimmer_name': swimmer_name,
                'event': f"{distance} {stroke.title()}",
                'event_raw': ev,
                'acc_placement': acc_placement,
                'acc_top_count': len(acc_times),
                'ncaa_placement': ncaa_placement,
                'ncaa_top_count': len(ncaa_times),
                'swimmer_best_time': swimmer_best_raw or 'N/A',
            })

            # Small pause to avoid rate limits
            await asyncio.sleep(0.5)

    # Write rows to CSV (ACC and NCAA placements)
    fieldnames = [
        'swimmer_id', 'swimmer_name', 'event', 'event_raw',
        'acc_placement', 'acc_top_count', 'ncaa_placement', 'ncaa_top_count',
        'swimmer_best_time'
    ]
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval='')
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote comparisons to {out_csv} ({len(rows)} rows)")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', default='M_Events/all_M_Events.json')
    parser.add_argument('--out', default='M_events_comparisons.csv')
    parser.add_argument('--region', default='division_1')
    parser.add_argument('--season', default='29')
    parser.add_argument('--pages', type=int, default=2)
    parser.add_argument('--gender', default='M', choices=['M', 'F', 'm', 'f'],
                        help='Gender to use for comparisons: M or F (default: M)')

    args = parser.parse_args()
    json_path = Path(args.json)
    out_csv = Path(args.out)

    asyncio.run(compare(json_path, out_csv, args.region, args.season, args.pages, args.gender))


if __name__ == '__main__':
    main()
