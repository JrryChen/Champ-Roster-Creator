import asyncio
from generate_championship_sheets import fetch_best_time_for_event

async def main():
    best = await fetch_best_time_for_event('1347491','Free',50,'Women','29')
    print('best 50 free:', best)

asyncio.run(main())
