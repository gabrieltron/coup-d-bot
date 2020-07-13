from dataclasses import dataclass, field
from random import shuffle
from typing import Dict, List

from .errors import ForeignAidNotFinished, GameAlreadyStarted, PlayerNotInGame
from .cards import Card
from .player import Player


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
    '''
    Class Game handles game's actions

    Args:
        group_id: Id where this game is running

    Attributes:
        group_id: Id where this game is running
        players: Map from the id of a player in the game for its
        Player object
        deck: Deck of available cards
        started: Wheter tha game has already started or not
    '''
    group_id: int
    players: Dict[int, Player] = field(default_factory=lambda: {})
    deck: List[Card] = field(default_factory=lambda: [])
    started: bool = False

    def start(self):
        '''
        Starts the game.
        '''
        if self.started:
            raise GameAlreadyStarted

        self.create_deck()
        self.started = True

    def add_player(self, player_id: int, player_name: str):
        '''
        Add a new player to the game

        Args:
            user_id: Id of the user to be added
            user_name: Name of the player to be added
        '''
        if self.started:
            raise GameAlreadyStarted

        player = Player(player_id, player_name)
        self.players[player_id] = player

    def deal_card(self, user_id: int, foreign_aid: bool = False):
        '''
        Deals a card to a player

        Args:
            user_id: Id of the user that will recieve the card
            foreign_aid: Wheter this card is a foreign aid card
        Returns:
            The type of the dealed card
        '''
        card = self.deck.pop()
        self.players[user_id].add_card(card, foreign_aid)
        return card

    def hide_card(self, player_id: int, card: Card):
        '''
        Move a card to the player's hidden hand

        Args:
            player_id: Id of the player to move the card from
            card: Card that will be move
        '''
        if player_id not in self.players:
            raise PlayerNotInGame

        player = self.players[player_id]
        player.hide_card(card)

    def show_card(self, player_id: int, card: Card):
        '''
        Move a card to the player's open hand

        Args:
            player_id: Id of the player to move the card from
            card: Card that will be move
        '''
        if player_id not in self.players:
            raise PlayerNotInGame

        player = self.players[player_id]
        player.show_card(card)

    def is_hidden(self, player_id: int, card: Card):
        '''
        Check if a card is hidden

        Args:
            player_id: Id of the player who owns the card
            card: Card to be checked
        Returns:
            Wheter the card is hidden or not
        '''
        if player_id not in self.players:
            raise PlayerNotInGame

        player = self.players[player_id]
        return player.is_hidden(card)

    def remove_card(self, player_id: int, card: Card):
        '''
        Remove a card from the player's hand. It also removes player
        from the game if it has no more cards

        Args:
            player_id: Id of the player to remove the card from
            card: Card that will be removed
        Returns:
            Wheter the player was removed from the game
        '''
        if player_id not in self.players:
            raise PlayerNotInGame

        player = self.players[player_id]
        player.remove_card(card)
        self.deck.append(card)
        shuffle(self.deck)

        if player.hand_size() == 0:
            del self.players[player.id]
            return True
        return False

    def foreign_aid(self, player_id: int):
        '''
        Gives random cards to a player until it has
        two times the cards it has

        Args:
            player_id: Id of the player using foreign aid
        Returns:
            List of cards given to the player
        '''
        if player_id not in self.players:
            raise PlayerNotInGame

        player = self.players[player_id]
        if player.foreign_aid_cards != 0:
            raise ForeignAidNotFinished

        return [
            self.deal_card(player_id, True) for _ in range(player.hand_size())
        ]

    def ended(self):
        '''
        Check if the game is over

        Returns:
            Wheter the game has ended or not
        '''
        return len(self.players == 1)

    def create_deck(self):
        '''
        Create the starting deck to play the game
        '''
        n_players = len(self.players)
        n_cards = N_CARDS[n_players]
        n_influences = len(Card)
        n_each_influence = n_cards // n_influences

        for _ in range(n_each_influence):
            for influence in Card:
                card = influence
                self.deck.append(card)

        shuffle(self.deck)

    def status(self):
        '''
        Get how many cards each player has

        Returns:
            String with how many cards each player has
        '''
        reply = ''
        for player in self.players.values():
            reply += f'{player.name} has {player.hand_size()} cards.\n'
        return reply
