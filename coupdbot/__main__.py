import asyncio

from carl import command
from telepot.aio import Bot
from telepot.aio.helper import Router
from telepot.aio.loop import MessageLoop

from .bot import CoupBot


def routes(coup_bot: CoupBot):
    '''
    Set routes to call functions when a command is read

    Args:
        coup_bot: The CoupBot instance that will be executed
    '''
    routes = {
        x: getattr(coup_bot, x)
        for x in
        ['new_game', 'join', 'start', 'actions', 'hide', 'show',
         'delete', 'foreign_aid', 'force_endgame', 'quit_game',
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
    '''
    Start the bot main loop

    Args:
        token: token of the bot created with BotFather
    '''
    bot = Bot(token)
    coup_bot = CoupBot(bot, (await bot.getMe())['username'])
    loop = asyncio.get_event_loop()
    loop.create_task(
        MessageLoop(
            coup_bot.bot,
            routes(coup_bot)
        ).run_forever()
    )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main.run_async())
    loop.run_forever()
