"""Compare swimmers to top times and append comparison columns to CSV

Usage:
  python compare_top_times.py <swimmers_csv> --event "<stroke>|<distance>|<gender>" [--region division_1|conference_3] [--season 29] [--pages 3]

Example:
  python compare_top_times.py test_swimmers.csv --event "1|50|M" --region division_1 --season 29 --pages 3
"""
import argparse
import asyncio
import csv
import sys
from pathlib import Path

# Ensure SwimScrape package is available on path (insert package root)
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SwimScrape'))

from SwimScrape.src.clients import TopTimesClient, SeasonalTimesClient


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


async def compare_csv(args):
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 1

    # Read CSV rows
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    # New column names
    event_label = args.event.replace('|', '_')
    season_col = f"season_best_{event_label}"
    swimmer_col = f"swimmer_time_{event_label}"
    diff_col = f"diff_to_top1_{event_label}"

    if season_col not in fieldnames:
        fieldnames.append(season_col)
    if swimmer_col not in fieldnames:
        fieldnames.append(swimmer_col)
    if diff_col not in fieldnames:
        fieldnames.append(diff_col)

    # Prepare clients
    top_client = TopTimesClient(timeout=15)

    # TopTimes expects numeric gender code in event and gender param; seasonal client accepts M/F
    parts = args.event.split('|')
    if len(parts) < 3:
        print("Event must be in format stroke|distance|gender (e.g. 1|50|M)")
        return 1
    stroke = parts[0]
    distance = parts[1]
    gender_letter = parts[2].upper()

    # TopTimes event uses numeric gender 1=M 2=F
    gender_num = '1' if gender_letter in ('M', '1') else '2'
    event_for_top = f"{stroke}|{distance}|{gender_num}"

    # Fetch top page(s) to estimate top1
    print(f"Fetching top times for event {event_for_top} in region {args.region} (pages={args.pages})...")
    try:
        top_times = await top_client.fetch_multiple_pages(
            event=event_for_top,
            gender=gender_letter,
            num_pages=args.pages,
            region=args.region,
            season_id=args.season,
            eventcourse='Y'
        )
    except Exception as e:
        print(f"Error fetching top times: {e}")
        top_times = []

    top_time_sec = None
    for t in top_times:
        try:
            sec = parse_time_to_seconds(t.time)
            if sec is not None:
                if top_time_sec is None or sec < top_time_sec:
                    top_time_sec = sec
        except Exception:
            continue

    if top_time_sec is None:
        print("No top times found; will record N/A in diff column")
    else:
        print(f"Top time (best) for event: {top_time_sec:.2f} seconds")

    # For each swimmer, fetch seasonal best and compare
    async def process_row(row):
        swimmer_id = (row.get('Swimmer ID') or row.get('swimmer_id') or row.get('SwimmerID') or '').strip()
        if not swimmer_id:
            row[season_col] = 'N/A'
            row[swimmer_col] = 'N/A'
            row[diff_col] = 'N/A'
            return

        seasonal_client = SeasonalTimesClient(swimmer_id, timeout=10)
        event_for_season = f"{stroke}|{distance}|{gender_letter}"

        try:
            times = await seasonal_client.fetch_times_by_event(event_for_season, course='Y')
        except Exception as e:
            print(f"  Error fetching seasonal times for {swimmer_id}: {e}")
            times = []

        swimmer_time = None
        if times:
            # take first (fastest) time
            swimmer_time = times[0].time

        if swimmer_time:
            sec = parse_time_to_seconds(swimmer_time)
            row[season_col] = swimmer_time
            row[swimmer_col] = swimmer_time
            if top_time_sec is not None and sec is not None:
                row[diff_col] = round(sec - top_time_sec, 2)
            else:
                row[diff_col] = 'N/A'
        else:
            row[season_col] = 'N/A'
            row[swimmer_col] = 'N/A'
            row[diff_col] = 'N/A'

    # Process rows sequentially to be gentle on API
    for i, row in enumerate(rows, 1):
        print(f"Processing row {i}/{len(rows)}: swimmer_id={(row.get('Swimmer ID') or row.get('swimmer_id') or '')}")
        await process_row(row)
        await asyncio.sleep(1.5)

    # Write updated CSV
    out_path = csv_path.with_name(csv_path.stem + f"_with_{event_label}.csv")
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval='')
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote updated CSV to {out_path}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', help='Path to swimmers CSV')
    parser.add_argument('--event', required=True, help='Event as stroke|distance|gender (e.g. 1|50|M)')
    parser.add_argument('--region', default='division_1', help='SwimCloud region code (division_1 or conference_3)')
    parser.add_argument('--season', default='29', help='Season id (default 29)')
    parser.add_argument('--pages', type=int, default=3, help='Number of pages to fetch from top times')

    args = parser.parse_args()

    asyncio.run(compare_csv(args))


if __name__ == '__main__':
    main()
