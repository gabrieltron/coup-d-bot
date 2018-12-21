import sys
import asyncio
import telepot

from dataclasses import dataclass, field
from carl import command
from pprint import pprint
from typing import Dict, List, Set
from random import shuffle
from textwrap import dedent

from telepot.aio import Bot
from telepot.aio.helper import Router, Editor
from telepot.aio.loop import MessageLoop
from telepot.namedtuple import (
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup,
    KeyboardButton, ReplyKeyboardRemove
)

@dataclass
class Card:
    value:str
    hidden:bool = False

@dataclass
class Player:
    name:str
    id:int
    group_id:int
    cards:Dict = field(default_factory=lambda: {})
    foreign_aid_cards:int = 0

    def __hash__(self):
        return hash(id)

    def add_card(self, card: Card, message_id: int):
        self.cards[message_id] = card

    def pop_card(self, message_id: int):
        card = self.cards[message_id]
        del self.cards[message_id]
        return card

    def hide_card(self, message_id: int):
        self.cards[message_id].hidden = True

    def show_card(self, message_id: int):
        self.cards[message_id].hidden = False

    def card_value(self, message_id: int):
        return self.cards[message_id].value

INFLUENCES = ['Duque', 'Capitão', 'Embaixador', 'Assassino', 'Duquesa']
N_CARDS = {
    1:15,
    2:15,
    3:15,
    4:15,
    5:15,
    6:15,
    7:20,
    8:20,
    9:25,
    10:25
}
@dataclass
class Game:
    players:Set = field(default_factory=lambda: set())
    deck:List = field(default_factory=lambda: [])
    started:bool = False
    last_status_sent:int = 0

    def add_player(self, player: Player):
        self.players.add(player)

    def remove_player(self, player: Player):
        self.players.remove(player)

    def create_deck(self):
        n_players = len(self.players)
        n_cards = N_CARDS[n_players]
        n_influences = len(INFLUENCES)
        n_each_influence = n_cards // n_influences

        for i in range(n_each_influence):
            for influence in INFLUENCES:
                card = Card(influence)
                self.deck.append(card)

        shuffle(self.deck)

    def random_card(self):
        # Since it's always shuffled the card is random
        return self.deck.pop()

    def stack_card(self, card: Card):
        card.hidden = False
        self.deck.append(card)
        shuffle(self.deck)

@dataclass
class CoupBot:
    bot:Bot
    games:Dict = field(default_factory=lambda: {})
    players:Dict = field(default_factory=lambda:{})

    async def start(self, message, _):
        chat_id = message['chat']['id']
        message_id = message['message_id']
        user_id = message['from']['id']
        chat_type = message['chat']['type']

        if chat_id in self.games:
            # there's already a game in this group
            reply = '''
                Já existe um jogo nesse chat, acabe-o primeiro. Ou dê um \
/force_endgame, mas isso interromperá o jogo no meio!
            '''
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        elif chat_type != 'group' and chat_type != 'supergroup':
            # tried to create a game outside a group 
            reply = '''
                O jogo deve ser iniciado em um grupo.
            '''
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
                reply = '''
                    Um jogo foi iniciado.
                '''
                await self.bot.sendMessage(
                    chat_id,
                    reply,
                    reply_to_message_id=message_id
                )
            else:
                del self.games[chat_id]

    async def join(self, message,_):
        chat_id = message['chat']['id']
        message_id = message['message_id']
        user_id = message['from']['id']
        chat_type = message['chat']['type']

        if chat_id not in self.games:
            # no game was started in this chat
            reply = '''
                O jogo ainda não foi iniciado. Inicie com /start
            '''
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        elif user_id in self.players:
            # player already in a game
            reply = '''
                Você já está em um jogo.
            '''
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        elif self.games[chat_id].started:
            # people already started playing, can't enter
            reply = '''
                Não é possível entrar em uma partida já iniciado. Espere ele \
acabar ou inicie outro. 
            '''
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

        elif chat_type != 'group' and chat_type != 'supergroup':
            # tried to join a game outside a group
            reply = '''
                Para juntar a um jogo, envie esse comando em um grupo em que \
o jogo tenha sido iniciado.
            '''
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
            reply = '''
                Você já está em um jogo. Saia ou acabe-o antes.
            '''
            await self.bot.sendMessage(
                player.group_id,
                reply,
                reply_to_message_id=message_id
            )
            return False

        try:
            private_reply = '''
                Você juntou-se a um jogo.
            '''
            keyboard_markup = ReplyKeyboardMarkup(keyboard=[
                    [KeyboardButton(text="Iniciar jogo"),
                    KeyboardButton(text="Sair do jogo")]
            ])

            await self.bot.sendMessage(
                player.id,
                private_reply,
                reply_markup=keyboard_markup
            )
        except:
            # couldn't send a private message
            error_message = '''
                Você não consegue fazer isso. Tenta me dar um oi no chat privado antes :)
            '''
            await self.bot.sendMessage(
                player.group_id,
                error_message,
                reply_to_message_id=message_id
            )
            return False

        game.add_player(player)
        self.players[player.id] = player
        return True

    async def start_game(self, message, _):
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
        actions = dedent(
            '''\
                *Influências e suas ações:*
                *Todos* - Pega 1 moeda. Pega duas moedas. Gasta 7 moedas para \
dar um golpe de estado (mata uma influência de um jogador a sua escolha). Com \
10 ou mais moedas golpe de estado é obrigatório.
                *Duque* - Pega 3 moedas. Bloqueia pegar duas moedas.
                *Capitão* - Rouba 2 moedas de um jogador. Bloqueia outro capitão.
                *Embaixador* - Pede ajuda externa, ou seja, compra o número de \
influencias que possui, elimina até ter o número de influências que \
tinha antes. Bloqueia capitão.
                *Assassino* - Mata uma influência de um jogador a sua escolha \
por 3 moedas.
                *Duquesa* - Bloqueia o assassino.
            '''
        )

        keyboard_markup = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="Ajuda externa"),
                KeyboardButton(text="Sair do jogo")]
        ])

        await self.bot.sendMessage(
            player.id,
            actions,
            reply_markup=keyboard_markup,
            parse_mode='Markdown'
        )

    async def send_random_card(self, player: Player, game: Game):
        new_card = game.random_card()
        keyboard = self.new_card_keyboard()
        new_card_message = await self.bot.sendMessage(
            player.id,
            new_card.value,
            reply_markup=keyboard
        )

        message_id = new_card_message['message_id']
        player.add_card(new_card, message_id)

    async def hide(self, message, _):
        chat_id = message['message']['chat']['id']
        message_id = message['message']['message_id']
        card_value = message['message']['text']

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text='Mostrar',
                callback_data='/show'
            ),
            InlineKeyboardButton(
                text='Remover',
                callback_data='/delete'
            )],
        ])

        player = self.players[chat_id]
        player.hide_card(message_id)
        await self.bot.editMessageText(
            msg_identifier=(chat_id, message_id),
            text='?',
            reply_markup=keyboard
        )

    async def show(self, message, _):
        chat_id = message['message']['chat']['id']
        message_id = message['message']['message_id']

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text='Esconder',
                callback_data='/hide'
            ),
            InlineKeyboardButton(
                text='Remover',
                callback_data='/delete'
            )],
        ])

        player = self.players[chat_id]
        player.show_card(message_id)
        card_value = player.card_value(message_id)
        await self.bot.editMessageText(
            msg_identifier=(chat_id, message_id),
            text=card_value,
            reply_markup=keyboard
        )

    async def delete(self, message, _):
        message_id = message['message']['message_id']
        chat_id = message['message']['chat']['id']
        player = self.players[chat_id]
        group_id = player.group_id
        game = self.games[group_id]

        card = player.pop_card(message_id)
        message = 'Uma carta de {} foi deletada.'.format(player.name)
        await self.bot.sendMessage(group_id, message)
        await self.bot.deleteMessage((chat_id, message_id))

        if not card.hidden and player.foreign_aid_cards == 0:
            # if a showing card is delete and the player isn't in a foreign
            # aid, the player just proved having an influence. Send another
            await self.send_random_card(player, game)
            message = '{} comprou uma nova carta'.format(player.name)
            await self.bot.sendMessage(group_id, message)

        elif player.foreign_aid_cards != 0:
            # The player is deciding which of the cards will stay after the aid
            player.foreign_aid_cards -= 1
            if player.foreign_aid_cards == 0:
                message = '{} terminou a ajuda externa'.format(player.name)
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
        message = 'Você ganhou o jogo'
        await self.bot.sendMessage(player.id, message)
        await self.remove_player(player, game)

        group_id = player.group_id
        message = 'Fim de jogo, {} venceu'.format(player.name)
        await self.bot.sendMessage(group_id, message)

        del self.players[player.id]
        del self.games[group_id]

    async def foreign_aid(self, message, _):
        player_id = message['from']['id']
        player = self.players[player_id]
        group_id = player.group_id

        if player.foreign_aid_cards == 0:
            message = '{} pediu ajuda externa.'.format(player.name)
            await self.bot.sendMessage(group_id, message)

            n_cards = len(player.cards)
            player.foreign_aid_cards = n_cards
            for i in range(n_cards):
                game = self.games[group_id]
                await self.send_random_card(player, game)
            
    async def quit_game(self, message, _):
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
        message = 'Você saiu do jogo.'
        await self.bot.sendMessage(
            player.id,
            message,
            reply_markup=ReplyKeyboardRemove()
        )

        del self.players[player.id]
        game.remove_player(player)

    async def force_endgame(self, message, _):
        chat_type = message['chat']['type']
        message_id = message['message_id']
        chat_id = message['chat']['id']
        if chat_type != 'group' and chat_type != 'supergroup':
            # tried to end a game outside a group
            reply = '''
                Essa ação só pode ser feita em um grupo com jogo iniciado.
            '''
            await self.bot.sendMessage(
                chat_id,
                reply, 
                reply_to_message_id=message_id
            )
        elif chat_id not in self.games:
            # no game in this group
            reply = '''
                Esse grupo ainda não iniciou um jogo.
            '''
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

            reply = '''
                Jogo terminado.
            '''
            await self.bot.sendMessage(
                chat_id,
                reply,
                reply_to_message_id=message_id
            )

    def new_card_keyboard(self):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text='Esconder',
                callback_data='/hide'
            ),
            InlineKeyboardButton(
                text='Remover',
                callback_data='/delete'
            )],
        ])
        return keyboard

    async def status(self, message, _):
        player_id = message['from']['id']
        chat_id = message['chat']['id']
        message_id = message['message_id']

        if player_id not in self.players:
            # tried to get status while not part of a game
            reply = '''
                Você não está em um jogo.
            '''
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
                reply += '*{}*: {} cartas.'.format(
                    player.name, len(player.cards)
                )

                if player.foreign_aid_cards != 0:
                    reply += ' {} cartas de ajuda externa'.format(
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

    async def help(self, message, _):
        chat_id = message['from']['id']
        message_id = message['message_id']
        reply = '''
            */start* - Começa o jogo no grupo de onde foi enviado.
            */join* - O usuário junta-se à partida ainda não iniciada.
            */force_endgame* - Força o fim da partida no grupo de onde foi enviado.
            */rules* - Envia uma mensagem com as regras do jogo.
            */status* - Envia para o grupo o status do jogo atual.
        '''
        await self.bot.sendMessage(
            chat_id, reply,
            reply_to_message_id=message_id,
            parse_mode='Markdown'
        )

    async def rules(self, message, _):
        chat_id = message['from']['id']
        message_id = message['message_id']
        reply = '''
            Cada jogador é um membro da corte francesa e possui duas influências. \
Cada jogador joga uma vez por rodada, em sua vez o jogador pode realizar uma ação, \
as ações que cada influência pode fazer são explicadas ao iniciar o jogo. Ao \
realizar uma ação de uma influência específica, o jogador deve declarar 'Sou x \
portanto faço y', ou outros jogadores podem aceitar ou contestar, alegando que \
o jogador da vez não possui a influência que declarou. Se o jogador da vez \
realmente estava blefando, ele esconde suas influências e deixa o contestador \
excluir uma delas, caso contrário o jogador mostra que realmente possuia a \
influência, exlcui ela (recebendo uma nova logo em seguida), e é o jogador \
que o acusou que esconde as cartas e tem uma influencia excluida pelo jogador da vez.
            Quando um jogador for alvo de um assassinato bem sucedido ou de um \
golpe de estado, ele deve esconder suas cartas e deixar o atacante selecionar uma \
para excluir.
            Para não tirar o aspecto social do jogo, esse bot não implementa \
as moedas. Isso não é nenhum impedimento para jogar, literalmente qualquer coisa \
pode representar as moedas, desde papéis picotados até as meias de natal que \
você ganhou da sua tia Bárbara e nunca tirou do pacote.
            Ganha o jogo a última pessoa que tiver influências sobrando.
        '''

    def default(self, message, _):
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
            if message_text == 'Iniciar jogo':
                return 'start_game', ([],)
            elif message_text == 'Ajuda externa':
                return 'foreign_aid', ([],)
            elif message_text == 'Sair do jogo':
                return 'quit_game', ([],)

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
