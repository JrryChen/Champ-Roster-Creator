import asyncio, json, httpx

async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get('https://www.swimcloud.com/api/swimmers/1347491/times_by_event/?event=1%7C50%7CY%7C2')
        print('status', resp.status_code)
        data = resp.json()
        results = data.get('results', []) if isinstance(data, dict) else data
        print('count', len(results))
        if results:
            print(json.dumps(results[0], indent=2))

asyncio.run(main())
