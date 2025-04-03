from src.pytrading212api.api import Trading212API
from src.pytrading212api.position import Position

import asyncio
import json


async def run():
    with open("login.json") as file:
        data = json.load(file)
    api = Trading212API(data["auth_token"])

    data = await api.get_positions()
    positions : list[Position] = []
    for position in data:
        positions.append(Position(api=api, data=position))
        

    for position in positions:
        print(position.average_price)

    data = await api.get_account_metadata()
    
    print(data)
    
    await api.close()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
