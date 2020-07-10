from dataclasses import dataclass, field
from textwrap import dedent
from typing import Dict

from telepot.aio import Bot
from telepot.namedtuple import (InlineKeyboardButton, InlineKeyboardMarkup,
                                KeyboardButton, ReplyKeyboardMarkup,
                                ReplyKeyboardRemove)

from .game import Game
from .player import Player


@dataclass
class CoupBot:
    bot:Bot
    games:Dict = field(default_factory=lambda: {})
    players:Dict = field(default_factory=lambda:{})

    async def start(self, message, args):
        chat_id = message['chat']['id']
        message_id = message['message_id']
        user_id = message['from']['id']
        chat_type = message['chat']['type']

        if chat_id in self.games:
            # there's already a game in this group
            reply = dedent('''\
                There's already a game in this chat, finish it firt.
                Alternatively, you can /force_game, but it'll interrupt
                the current game!
            ''')
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        elif chat_type != 'group' and chat_type != 'supergroup':
            # tried to create a game outside a group
            reply = 'The game must be started in a group.'
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        else:
            game = Game()
            self.games[chat_id] = game
            user_name = message['from']['first_name']
            player = Player(user_name, user_id, chat_id)

            player_added = await self.add_player(message_id, player, game)
            if player_added:
                reply = 'A game was started.'
                await self.bot.sendMessage(
                    chat_id,
                    reply,
                    reply_to_message_id=message_id
                )
            else:
                del self.games[chat_id]

    async def join(self, message,args):
        chat_id = message['chat']['id']
        message_id = message['message_id']
        user_id = message['from']['id']
        chat_type = message['chat']['type']

        if chat_id not in self.games:
            # no game was started in this chat
            reply = 'The game was not start. Start it using /start'
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        elif user_id in self.players:
            # player already in a game
            reply = 'You\'re already in a game.'
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        elif self.games[chat_id].started:
            # people already started playing, can't enter
            reply = dedent('''\
                You can't enter a match that has already started.
                Wait for it to end or start a new one.
            ''')
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        elif chat_type != 'group' and chat_type != 'supergroup':
            # tried to join a game outside a group
            reply = dedent('''\
                To join a game send this command to a group where the
                game has been started.
            ''')
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        else:
            user_name = message['from']['first_name']
            player = Player(user_name, user_id, chat_id)
            game = self.games[chat_id]
            await self.add_player(message_id, player, game)

    async def add_player(self, message_id: int, player: Player, game: Game):
        if player.id in self.players:
            # this player is already in a game
            reply = 'You\'re already in a game. Quit or finish it first.'
            await self.bot.sendMessage(
                player.group_id,
                reply,
                reply_to_message_id=message_id
            )
            return False

        try:
            private_reply = 'You joined a game.'
            keyboard_markup = ReplyKeyboardMarkup(keyboard=[
                    [KeyboardButton(text='Start game'),
                    KeyboardButton(text='Quit game')]
            ])

            await self.bot.sendMessage(
                player.id,
                private_reply,
                reply_markup=keyboard_markup
            )
        except:
            # couldn't send a private message
            error_message = dedent('''
                You can't do this. Try sending me a hi in
                private first :)
            ''')
            await self.bot.sendMessage(
                player.group_id,
                error_message,
                reply_to_message_id=message_id
            )
            return False

        game.add_player(player)
        self.players[player.id] = player
        return True

    async def start_game(self, message, args):
        player_id = message['from']['id']
        group_id = self.players[player_id].group_id
        game = self.games[group_id]

        game.create_deck()
        await self.distribute_cards(game)

    async def distribute_cards(self, game: Game):
        for player in game.players:
            await self.send_actions(player)
            for i in range(2):
                await self.send_random_card(player, game)

    async def send_actions(self, player: Player):
        actions = dedent('''\
            *Influences and it's actions*
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

        keyboard_markup = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text='Foreign aid'),
                KeyboardButton(text='Quit game')]
        ])

        await self.bot.sendMessage(
            player.id,
            actions,
            reply_markup=keyboard_markup,
            parse_mode='Markdown'
        )

    async def send_random_card(self, player: Player, game: Game):
        new_card = game.random_card()

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text= 'Hide',
                callback_data='/hide'
            ),
            InlineKeyboardButton(
                text= 'Remove',
                callback_data='/delete'
            )],
        ])

        new_card_message = await self.bot.sendMessage(
            player.id,
            new_card.value,
            reply_markup=keyboard
        )

        message_id = new_card_message['message_id']
        player.add_card(new_card, message_id)

    async def hide(self, message, args):
        chat_id = message['message']['chat']['id']
        message_id = message['message']['message_id']
        card_value = message['message']['text']
        player = self.players[chat_id]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text= 'Show',
                callback_data='/show'
            ),
            InlineKeyboardButton(
                text= 'Remove',
                callback_data='/delete'
            )],
        ])

        player.hide_card(message_id)
        await self.bot.editMessageText(
            msg_identifier=(chat_id, message_id),
            text='?',
            reply_markup=keyboard
        )

    async def show(self, message, args):
        chat_id = message['message']['chat']['id']
        message_id = message['message']['message_id']
        player = self.players[chat_id]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text= 'Hide',
                callback_data='/hide'
            ),
            InlineKeyboardButton(
                text= 'Remove',
                callback_data='/delete'
            )],
        ])

        player = self.players[chat_id]
        player.show_card(message_id)
        card_value = player.card_value(message_id)
        await self.bot.editMessageText(
            msg_identifier=(chat_id, message_id),
            text = card_value,
            reply_markup=keyboard
        )

    async def delete(self, message, args):
        message_id = message['message']['message_id']
        chat_id = message['message']['chat']['id']
        player = self.players[chat_id]
        group_id = player.group_id
        game = self.games[group_id]

        card = player.pop_card(message_id)
        message = 'A card from {} was deleted.'.format(player.name)
        await self.bot.sendMessage(group_id, message)
        await self.bot.deleteMessage((chat_id, message_id))

        if not card.hidden and player.foreign_aid_cards == 0:
            # if a showing card is delete and the player isn't in a foreign
            # aid, the player just proved having an influence. Send another
            await self.send_random_card(player, game)
            message = '{} bought a new card'.format(player.name)
            await self.bot.sendMessage(group_id, message)

        elif player.foreign_aid_cards != 0:
            # The player is deciding which of the cards will stay after the aid
            player.foreign_aid_cards -= 1
            if player.foreign_aid_cards == 0:
                message = '{} finished a foreign aid'.format(player.name)
                await self.bot.sendMessage(group_id, message)

        game.stack_card(card)
        if len(player.cards) == 0:
            # player has no more cards
            await self.remove_player(player, game)
            endgame = self.is_endgame(game)
            if endgame:
                await self.finish_game(game)

    def is_endgame(self, game: Game):
        if len(game.players) <= 1:
            return True
        else:
            return False

    async def finish_game(self, game: Game):
        player = next(iter(game.players))

        message = 'You won the game'
        await self.bot.sendMessage(player.id, message)
        await self.remove_player(player, game)

        group_id = player.group_id
        message = 'Game over, {} won'.format(player.name)
        await self.bot.sendMessage(group_id, message)

        del self.games[group_id]

    async def foreign_aid(self, message, args):
        player_id = message['from']['id']
        player = self.players[player_id]
        group_id = player.group_id

        if player.foreign_aid_cards == 0:
            message = '{} used foreign aid.'.format(player.name)
            await self.bot.sendMessage(group_id, message)

            n_cards = len(player.cards)
            player.foreign_aid_cards = n_cards
            for i in range(n_cards):
                game = self.games[group_id]
                await self.send_random_card(player, game)

    async def quit_game(self, message, args):
        player_id = message['from']['id']
        player = self.players[player_id]
        group_id = player.group_id
        game = self.games[group_id]

        await self.remove_player(player, game)
        endgame = self.is_endgame(game)
        if endgame:
            await self.finish_game(game)

    async def remove_player(self, player: Player, game: Game):
        for message_id in dict(player.cards):
            card = player.pop_card(message_id)
            game.stack_card(card)
            await self.bot.deleteMessage((player.id, message_id))
        message = 'You quitted the game.'
        await self.bot.sendMessage(
            player.id,
            message,
            reply_markup=ReplyKeyboardRemove()
        )

        del self.players[player.id]
        game.remove_player(player)

    async def force_endgame(self, message, args):
        chat_type = message['chat']['type']
        message_id = message['message_id']
        chat_id = message['chat']['id']

        if chat_type != 'group' and chat_type != 'supergroup':
            # tried to end a game outside a group
            reply = dedent('''\
                This action can only be done in a group with a started
                game.
            ''')
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )
        elif chat_id not in self.games:
            # no game in this group
            reply = 'This group haven\'t started a game.'
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )
        else:
            game = self.games[chat_id]
            for player in set(game.players):
                await self.remove_player(player, game)
            del self.games[chat_id]

            reply = 'Game over.'
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

    async def status(self, message, args):
        player_id = message['from']['id']
        chat_id = message['chat']['id']
        message_id = message['message_id']

        if player_id not in self.players:
            # tried to get status while not part of a game
            reply = 'You\'re not in a game.'
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )
        else:
            group_id = self.players[player_id].group_id
            game = self.games[group_id]

            reply = ''
            for player in game.players:
                reply += '*{}*: {} card(s).'.format(
                    player.name, len(player.cards)
                )

                if player.foreign_aid_cards != 0:
                    reply += ' {} foreign aid card(s)'.format(
                        player.foreign_aid_cards
                    )

                reply += '\n'

            if game.last_status_sent != 0:
                await self.bot.deleteMessage((group_id, game.last_status_sent))
            sent_message = await self.bot.sendMessage(
                group_id,
                reply,
                parse_mode='Markdown'
            )
            game.last_status_sent = sent_message['message_id']

    async def help(self, message, args):
        chat_id = message['chat']['id']
        message_id = message['message_id']

        # ok. internacionalization is weird and this way was the only one I
        # could manage to generate a correct template for i18n
        reply = dedent('''\
            */start* - Start a game in a group.
            */join* - User joins the game if that match
            hasn't started.
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

    async def rules(self, message, args):
        chat_id = message['from']['id']
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

        await self.bot.sendMessage(chat_id, reply, reply_to_message_id=message_id)

    def default(self, message, args):
        pass

    def read_command(self, message):
        if 'text' in message:
            message_text = message['text']
        else:
            message_text = message['data']

        if message_text[0] == '/':
            message_text = message_text.split()
            command = message_text[0][1:]
            args = message_text[1:]

            return command, (args,)
        else:
            if message_text == 'Start game':
                return 'start_game', ([],)
            elif message_text == 'Foreign aid':
                return 'foreign_aid', ([],)
            elif message_text == 'Quit game':
                return 'quit_game', ([],)
