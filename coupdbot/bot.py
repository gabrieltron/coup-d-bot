from dataclasses import dataclass, field
from textwrap import dedent
from typing import Any, Dict

from telepot.aio import Bot
from telepot.namedtuple import (InlineKeyboardButton, InlineKeyboardMarkup,
                                KeyboardButton, ReplyKeyboardMarkup)

from .errors import ForeignAidNotFinished, GameAlreadyStarted
from .cards import Card
from .game import Game


@dataclass
class CoupBot:
    '''
    The CoupBot handles user interaction

    Args:
        bot: Bot handler

    Attributes:
        bot: Bot handler
        games: Map from group id to its Game object.
        player_to_game: Map from user id to its game.
        dealt_cards: Nested map from user_id and message_id to which card
        that message represents.
    '''
    bot: Bot
    games: Dict[int, Game] = field(default_factory=lambda: {})
    player_to_game: Dict[int, Game] = field(default_factory=lambda: {})
    dealt_cards: Dict[int, Dict[int, Card]] = field(default_factory=lambda: {})

    async def new_game(self, message: Dict[str, Any], _):
        '''
        Prepare to start a new game inside a group

        Args:
            message: a dict containing message data
        '''
        chat_id = message['chat']['id']
        message_id = message['message_id']
        chat_type = message['chat']['type']

        if chat_id in self.games:
            reply = dedent('''\
                There's already a game in this chat, finish it firt.
                Alternatively, you can /force_game, but it'll interrupt
                the current game!
            ''')

        elif chat_type not in ('group', 'supergroup'):
            reply = 'The game must be started in a group.'

        else:
            game = Game(chat_id)
            self.games[chat_id] = game
            reply = dedent('''\
                A new game is ready! Send a /join to join it.
                Send a /start here once everybody is in.
            ''')

        await self.bot.sendMessage(
            chat_id,
            reply,
            reply_to_message_id=message_id
        )

    async def join(self, message: Dict[str, Any], _):
        '''
        Add a player to the game, if it has not started yet

        Args:
            message: a dict containing message data
        '''
        chat_id = message['chat']['id']
        message_id = message['message_id']
        user_id = message['from']['id']
        user_name = message['from']['first_name']
        chat_type = message['chat']['type']

        if chat_type not in ('group', 'supergroup'):
            reply = 'You must join a game inside a group.'

        elif user_id in self.player_to_game:
            reply = 'You\'re already in a game.'

        elif chat_id not in self.games:
            reply = 'The game was not created. Create it using /new_game'

        else:
            try:
                game = self.games[chat_id]
                game.add_player(user_id, user_name)
                self.player_to_game[user_id] = game
                self.dealt_cards[user_id] = {}
                reply = 'You joined the game!'
            except GameAlreadyStarted:
                reply = 'Can\'t join middle game. Finish it or /force_end first'

        await self.bot.sendMessage(
            chat_id,
            reply,
            reply_to_message_id=message_id
        )

    async def start(self, message: Dict[str, Any], _):
        '''
        Start the game and send cards to players

        Args:
            message: a dict containing message data
        '''
        chat_id = message['chat']['id']
        message_id = message['message_id']

        keyboard_markup = None
        try:
            game = self.games[chat_id]
            game.start()
            for user_id in game.players.keys():
                for _ in range(2):
                    await self.deal_random_card(user_id)


            reply = 'Game started!'
            keyboard_markup = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text='Foreign aid'),
                 KeyboardButton(text='Quit game')]
            ])
        except KeyError:
            reply = 'The game was not created. Create it using /new_game'
        except GameAlreadyStarted:
            reply = 'Can\'t join middle game. Finish it or /force_end first'

        await self.bot.sendMessage(
            chat_id,
            reply,
            reply_to_message_id=message_id,
            reply_markup=keyboard_markup,
        )

    async def deal_random_card(self, user_id: int):
        '''
        Deal a random card to a player

        Args:
            user_id: Id of the user to deal the card to
        '''
        game = self.player_to_game[user_id]
        card = game.deal_card(user_id)
        await self.deal_card(user_id, card)

    async def deal_card(self, user_id: int, card: Card):
        '''
        Send the card to the player's chat

        Args:
            user_id: Id to where the card will be sent
            card: Card that will be sent
        '''
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text='Hide',
                callback_data='/hide'
            ),
             InlineKeyboardButton(
                 text='Remove',
                 callback_data='/delete'
             )],
        ])
        message = await self.bot.sendMessage(
            user_id,
            card.name,
            reply_markup=keyboard
        )
        message_id = message['message_id']
        self.dealt_cards[user_id][message_id] = card

    async def foreign_aid(self, message, _):
        '''
        Start a foreign aid action

        Args:
            message: a dict containing message data
        '''
        player_id = message['from']['id']
        game = self.player_to_game[player_id]

        try:
            cards = game.foreign_aid(player_id)
            for card in cards:
                await self.deal_card(player_id, card)
        except ForeignAidNotFinished:
            await self.bot.sendMessage(
                player_id,
                'You need remove cards from previous Foreign Aid first',
            )

    async def actions(self, message: Dict[str, Any], _):
        '''
        Sends a list of the possible actions
        '''
        chat_id = message['chat']['id']
        actions = dedent('''\
            *Influences and its actions*
            *All* - Get 1 coin. Get 2 coins. Spend 7 coins to give
            a coup d'etat (kill a influence of a player of your choice).
            With 10 or more coins, coup d'etat is mandatory.
            *Duke* - Get 3 coins. Blocks a player of getting 2
            coins.
            *Captain* - Steals 2 coins of another player. Blocks
            ther captains
            *Embassador* - Asks for foreign aid, buy the number of
            influeces you possess, eliminates them until you have the number
            of you had before. Blocks captains.
            *Assassin* - Kills a influence of a player of your
            choice for 3 coins.
            *Duchess* - Blocks assassins.
        ''')

        await self.bot.sendMessage(
            chat_id,
            actions,
            parse_mode='Markdown'
        )

    async def hide(self, message, _):
        '''
        Edit message to hide a card from the player

        Args:
            message: a dict containing message data
        '''
        chat_id = message['message']['chat']['id']
        message_id = message['message']['message_id']

        if chat_id not in self.player_to_game:
            return await self.bot.sendMessage(
                chat_id,
                'You are not in a game',
                message_id
            )

        game = self.player_to_game[chat_id]
        card = self.dealt_cards[chat_id][message_id]
        game.hide_card(chat_id, card)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text='Show',
                callback_data='/show'
            ),
             InlineKeyboardButton(
                 text='Remove',
                 callback_data='/delete'
            )],
        ])

        await self.bot.editMessageText(
            msg_identifier=(chat_id, message_id),
            text='?',
            reply_markup=keyboard
        )

    async def show(self, message, _):
        '''
        Edit message to show a hidden card

        Args:
            message: a dict containing message data
        '''
        chat_id = message['message']['chat']['id']
        message_id = message['message']['message_id']
        if chat_id not in self.player_to_game:
            return await self.bot.sendMessage(
                chat_id,
                'You are not in a game',
                message_id
            )

        game = self.player_to_game[chat_id]
        card = self.dealt_cards[chat_id][message_id]
        game.show_card(chat_id, card)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text='Hide',
                callback_data='/hide'
            ),
             InlineKeyboardButton(
                 text='Remove',
                 callback_data='/delete'
            )],
        ])

        await self.bot.editMessageText(
            msg_identifier=(chat_id, message_id),
            text=card.name,
            reply_markup=keyboard
        )

    async def delete(self, message, _):
        '''
        Deletes a card from the player's hand. Remvoes player from game
        if it has no cards left, and finishes the game if there's only
        one player left

        Args:
            message: a dict containing message data
        '''
        message_id = message['message']['message_id']
        chat_id = message['message']['chat']['id']
        player_name = message['message']['chat']['first_name']

        game = self.player_to_game[chat_id]
        card = self.dealt_cards[chat_id][message_id]
        was_hidden = game.is_hidden(chat_id, card)
        player_removed = game.remove_card(chat_id, card)

        del self.dealt_cards[chat_id][message_id]
        await self.bot.deleteMessage((chat_id, message_id))
        message = f'A card from {player_name} was deleted.'
        await self.bot.sendMessage(game.group_id, message)

        if player_removed:
            del self.player_to_game[chat_id]
            del self.dealt_cards[chat_id]
            if game.ended():
                await self.end_game(game)

        elif not was_hidden:
            await self.deal_random_card(chat_id)

    async def end_game(self, game):
        '''
        Finish current game

        Args:
            game: Game to be finished
        '''
        group_id = game.group_id
        reply = 'Game over.'
        if len(game.players) == 1:
            winner = next(iter(game.players.values()))
            reply += f' {winner.name} is the winner!'

        for player in game.players.values():
            for message_id in self.dealt_cards[player.id].keys():
                await self.bot.deleteMessage((player.id, message_id))
            del self.player_to_game[player.id]
            del self.dealt_cards[player.id]

        del self.games[group_id]

        await self.bot.sendMessage(
            group_id,
            reply,
        )

    async def force_endgame(self, message, _):
        '''
        Force the end of the current game

        Args:
            message: a dict containing message data
        '''
        chat_id = message['chat']['id']

        if chat_id not in self.games:
            return await self.bot.sendMessage(
                chat_id,
                'Game not started here',
            )

        game = self.games[chat_id]
        await self.end_game(game)

    async def status(self, message, _):
        '''
        Sends a message with the status of the players' hands

        Args:
            message: a dict containing message data
        '''
        player_id = message['from']['id']
        chat_id = message['chat']['id']
        message_id = message['message_id']

        if player_id not in self.player_to_game:
            reply = 'You\'re not in a game.'
        else:
            game = self.player_to_game[player_id]
            reply = game.status()

        await self.bot.sendMessage(
            chat_id,
            reply,
            reply_to_message_id=message_id
        )

    async def help(self, message, _):
        '''
        Send a message with bot's actions

        Args:
            message: a dict containing message data
        '''
        chat_id = message['chat']['id']
        message_id = message['message_id']

        reply = dedent('''\
            */new_game* - Prepare to start a new game.
            */join* - User joins the game if that match
            hasn't started.
            */start* - Start a game in a group.
            */force_endgame* - Forces the end of the game in a group.
            */rules* - Send a message with the game's rules.
            */status* - Send to the group the current state of the
            game.
        ''')

        await self.bot.sendMessage(
            chat_id, reply,
            reply_to_message_id=message_id,
            parse_mode='Markdown'
        )

    async def rules(self, message, _):
        '''
        Send a message with bot's actions

        Args:
            message: a dict containing message data
        '''
        chat_id = message['chat']['id']
        message_id = message['message_id']

        reply = dedent('''\
            Each player is a member of the french court and possess
            two influences. Each player playes once per round, on its
            turn the player performs an action, which actions each influence
            can perform will be explained at the beginning of the game.
            When an action from a specific influence is performed, the player
            must declare "I'm X and I'll do Y", other players com accept or
            contest, claiming the player doesn't have it influence it claims
            to have. If the player was really bluffing, it hides its
            influences and let the contestant player choose a card to delete,
            otherwise the player shows that it really had that influence and
            it's the contestant player that hide it's cards and allow a card
            to be deleted.
            When a player is a victm of the assassin or a coup d'etat,
            it must hide it's cards and allow the attacker to choose one to
            remove.
            In order to keep the social aspect of the game, this bot
            doesn't implement coins. This is no obstacle, literally anything
            can represent coins, from cutted paper to the christmas socks
            your aunt Barbara gave to you and you never unpacked.
            Wins the game the last player with at least one influence
            remaining.
        ''')

        await self.bot.sendMessage(
            chat_id,
            reply,
            reply_to_message_id=message_id
        )

    def default(self, _, __):
        '''
        Default action. It gets called when the bot
        reads an invalid command.
        '''

    def read_command(self, message):
        '''
        Read command to see which function to call

        Args:
            message: a dict containing message data
        '''
        if 'text' in message:
            message_text = message['text']
        else:
            message_text = message['data']

        if message_text[0] == '/':
            message_text = message_text.split()
            command = message_text[0][1:]
            args = message_text[1:]

            return command, (args,)

        if message_text == 'Start game':
            return 'start_game', ([],)

        if message_text == 'Foreign aid':
            return 'foreign_aid', ([],)

        if message_text == 'Quit game':
            return 'quit_game', ([],)

        return 'default', ([],)
