class CoupDBotError(Exception):
    '''
    General exception from the bot
    '''


class GameError(CoupDBotError):
    '''
    General exception from game errors
    '''


class PlayerError(CoupDBotError):
    '''
    General exception from player errors
    '''


class GameAlreadyStarted(GameError):
    '''
    Exception cause by trying to use preparing actions
    when the game has already started
    '''


class PlayerNotInGame(GameError):
    '''
    Exception cause by trying to access a player that is not
    in the game
    '''


class ForeignAidNotFinished(GameError):
    '''
    Exception caused by trying to use foreign aid
    while the player is still holding cards from a previous one
    '''


class CardNotFound(Exception):
    '''
    Exception caused by trying to handle a card
    that is not in the container
    '''
