import asyncio

from carl import command
from telepot.aio import Bot
from telepot.aio.helper import Router
from telepot.aio.loop import MessageLoop

from .bot import CoupBot


def routes(coup_bot: CoupBot):
    routes = {
        x: getattr(coup_bot, x)
        for x in
        ['start', 'join', 'start_game', 'hide', 'show',
        'delete', 'foreign_aid', 'quit_game', 'force_endgame',
        'help', 'rules', 'status']
    }
    routes[None] = coup_bot.default

    router = Router(
        coup_bot.read_command,
        routes,
    )

    return router.route

@command
async def main(token):
    coup_bot = CoupBot(Bot(token))
    loop = asyncio.get_event_loop()
    loop.create_task(
        MessageLoop(coup_bot.bot, routes(coup_bot)
    ).run_forever())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main.run_async())
    loop.run_forever()
