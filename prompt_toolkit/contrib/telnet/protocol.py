"""
Parser for the Telnet protocol. (Not a complete implementation of the telnet
specification, but sufficient for a command line interface.)

Inspired by `Twisted.conch.telnet`.
"""
import struct

from .log import logger

__all__ = [
    'TelnetProtocolParser',
]

# Telnet constants.
NOP      = bytes((0,))
SGA      = bytes((3,))

IAC      = bytes((255,))
DO       = bytes((253,))
DONT     = bytes((254,))
LINEMODE = bytes((34,))
SB       = bytes((250,))
WILL     = bytes((251,))
WONT     = bytes((252,))
MODE     = bytes((1,))
SE       = bytes((240,))
ECHO     = bytes((1,))
NAWS     = bytes((31,))
LINEMODE = bytes((34,))
SUPPRESS_GO_AHEAD = bytes((3,))

DM       = bytes((242,))
BRK      = bytes((243,))
IP       = bytes((244,))
AO       = bytes((245,))
AYT      = bytes((246,))
EC       = bytes((247,))
EL       = bytes((248,))
GA       = bytes((249,))


class TelnetProtocolParser:
    """
    Parser for the Telnet protocol.
    Usage::

        def data_received(data):
            print(data)

        def size_received(rows, columns):
            print(rows, columns)

        p = TelnetProtocolParser(data_received, size_received)
        p.feed(binary_data)
    """
    def __init__(self, data_received_callback, size_received_callback):
        self.data_received_callback = data_received_callback
        self.size_received_callback = size_received_callback

        self._parser = self._parse_coroutine()
        self._parser.send(None)

    def received_data(self, data):
        self.data_received_callback(data)

    def do_received(self, data):
        """ Received telnet DO command. """
        logger.info('DO %r', data)

    def dont_received(self, data):
        """ Received telnet DONT command. """
        logger.info('DONT %r', data)

    def will_received(self, data):
        """ Received telnet WILL command. """
        logger.info('WILL %r', data)

    def wont_received(self, data):
        """ Received telnet WONT command. """
        logger.info('WONT %r', data)

    def command_received(self, command, data):
        if command == DO:
            self.do_received(data)

        elif command == DONT:
            self.dont_received(data)

        elif command == WILL:
            self.will_received(data)

        elif command == WONT:
            self.wont_received(data)

        else:
            logger.info('command received %r %r', command, data)

    def naws(self, data):
        """
        Received NAWS. (Window dimensions.)
        """
        if len(data) == 4:
            # NOTE: the first parameter of struct.unpack should be
            # a 'str' object. This crashes on OSX otherwise.
            columns, rows = struct.unpack(str('!HH'), data)
            self.size_received_callback(rows, columns)
        else:
            logger.warning('Wrong number of NAWS bytes')

    def negotiate(self, data):
        """
        Got negotiate data.
        """
        command, payload = data[0:1], data[1:]
        assert isinstance(command, bytes)

        if command == NAWS:
            self.naws(payload)
        else:
            logger.info('Negotiate (%r got bytes)', len(data))

    def _parse_coroutine(self):
        """
        Parser state machine.
        Every 'yield' expression returns the next byte.
        """
        while True:
            d = yield

            if d == bytes((0,)):
                pass  # NOP

            # Go to state escaped.
            elif d == IAC:
                d2 = yield

                if d2 == IAC:
                    self.received_data(d2)

                # Handle simple commands.
                elif d2 in (NOP, DM, BRK, IP, AO, AYT, EC, EL, GA):
                    self.command_received(d2, None)

                # Handle IAC-[DO/DONT/WILL/WONT] commands.
                elif d2 in (DO, DONT, WILL, WONT):
                    d3 = yield
                    self.command_received(d2, d3)

                # Subnegotiation
                elif d2 == SB:
                    # Consume everything until next IAC-SE
                    data = []

                    while True:
                        d3 = yield

                        if d3 == IAC:
                            d4 = yield
                            if d4 == SE:
                                break
                            else:
                                data.append(d4)
                        else:
                            data.append(d3)

                    self.negotiate(b''.join(data))
            else:
                self.received_data(d)

    def feed(self, data):
        """
        Feed data to the parser.
        """
        assert isinstance(data, bytes)
        for b in iter(data):
            self._parser.send(bytes((b,)))
