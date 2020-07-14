from dataclasses import dataclass, field
from typing import List

from .cards import Card
from .errors import CardNotFound


@dataclass
class Player:
    '''
    Class Player handles player data

    Args:
        id: Player's id

    Attributes:
        id: Player's id
        name: Player's name
        cards: List with open cards held by the player
        hidden_cards: List with hidden cards held by the player
        foreign_aid_cards: How many cards, either open or hidden,
        comes from foreign aid.
    '''
    id: int
    name: str
    cards: List = field(default_factory=lambda: [])
    hidden_cards: List = field(default_factory=lambda: [])
    foreign_aid_cards: int = 0

    def add_card(self, card: Card, foreign_aid: bool = False):
        '''
        Add a card to the set of cards

        Args:
            card: Card to be added
            foreign_aid: Wheter this card is a foreign aid card
        '''
        if foreign_aid:
            self.foreign_aid_cards += 1

        self.cards.append(card)

    def hide_card(self, card: Card):
        '''
        Move a card to the hidden hand

        Args:
            card: Card to be moved
        '''
        if card not in self.cards:
            raise CardNotFound

        self.cards.remove(card)
        self.hidden_cards.append(card)

    def show_card(self, card: Card):
        '''
        Move a card to the open hand

        Args:
            card: Card to be moved
        '''
        if card not in self.hidden_cards:
            raise CardNotFound

        self.hidden_cards.remove(card)
        self.cards.append(card)

    def remove_card(self, card: Card):
        '''
        Remove a card from hand. It will first try to remove from
        hidden hand, if card is not there it'll try to remove from
        open hand

        Args:
            card: Card to me removed
        '''
        if card in self.hidden_cards:
            self.hidden_cards.remove(card)
            self.foreign_aid_cards = max(0, self.foreign_aid_cards-1)
        elif card in self.cards:
            self.cards.remove(card)
            self.foreign_aid_cards = max(0, self.foreign_aid_cards-1)
        else:
            raise CardNotFound

    def hand(self):
        '''
        Returns all cards in hand

        Returns:
            A list with all cards the player holds
        '''
        return self.cards + self.hidden_cards

    def is_hidden(self, card: Card):
        '''
        Check if a card is hidden

        Args:
            card: Card to be checked
        Returns:
            Wheter the card is hidden or not
        '''
        return card in self.hidden_cards

    def hand_size(self):
        '''
        Returns how many cards the player has

        Returns:
            How many cards the player has
        '''
        return len(self.hand())
