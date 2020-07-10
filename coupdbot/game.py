from dataclasses import dataclass, field
from random import shuffle
from typing import List, Set

from .player import Card, Player


INFLUENCES = ['Duke', 'Captain', 'Embassador',
              'Assassin', 'Duchess']

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
