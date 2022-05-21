from .exchange import Exchange


class Ftx(Exchange):
    def __init__(self, config):
        super().__init__('ftx', config)