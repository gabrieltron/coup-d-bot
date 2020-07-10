from dataclasses import dataclass, field
from typing import Dict


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
