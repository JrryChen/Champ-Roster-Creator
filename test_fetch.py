import asyncio
import sys
sys.path.insert(0, 'C:\\Users\\chess\\OneDrive\\Documents\\Champ-Roster-Creator')
from generate_championship_sheets import fetch_best_time_for_event

async def main():
    result = await fetch_best_time_for_event('1347491', 'Free', 50, 'Women', '29')
    print(f"Result: {result}")

asyncio.run(main())
