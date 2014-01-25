#!/usr/bin/env python

import unittest

from cmdline import InputStream, CommandLineHandler


class CLILogger(object):
    """ Dummy CLI class that records all the called methods. """
    def __init__(self):
        self.log = []

    def __getattr__(self, name):
        def handler(*a):
            self.log.append((name,) + a)
        return handler


class InputProtocolTest(unittest.TestCase):
    def setUp(self):
        self.stream = InputStream()
        self.cli = CLILogger()
        self.stream.attach(self.cli)

    def test_simple_feed_text(self):
        self.stream.feed('test')
        self.assertEqual(self.cli.log, [
                        ('insert_data', 't'),
                        ('insert_data', 'e'),
                        ('insert_data', 's'),
                        ('insert_data', 't')
                    ])

    def test_some_control_sequences(self):
        self.stream.feed('t\x01e\x02s\x03t\x04')
        self.assertEqual(self.cli.log, [
                        ('insert_data', 't'),
                        ('ctrl_a', ),
                        ('insert_data', 'e'),
                        ('ctrl_b', ),
                        ('insert_data', 's'),
                        ('ctrl_c', ),
                        ('insert_data', 't'),
                        ('ctrl_d', ),
                    ])

    def test_enter(self):
        self.stream.feed('A\rB\nC\t')
        self.assertEqual(self.cli.log, [
                        ('insert_data', 'A'),
                        ('enter', ),
                        ('insert_data', 'B'),
                        ('enter', ),
                        ('insert_data', 'C'),
                        ('tab', ),
                    ])

    def test_cursor_movement(self):
        self.stream.feed('\x1b[AA\x1b[BB\x1b[CC\x1b[DD')
        self.assertEqual(self.cli.log, [
                        ('cursor_up',),
                        ('insert_data', 'A'),
                        ('cursor_down',),
                        ('insert_data', 'B'),
                        ('cursor_right',),
                        ('insert_data', 'C'),
                        ('cursor_left',),
                        ('insert_data', 'D'),
                    ])


class HandlerTest(unittest.TestCase):
    def setUp(self):
        self.cli = CommandLineHandler()

    def test_setup(self):
        self.assertEqual(self.cli.text, '')
        self.assertEqual(self.cli.cursor_position, 0)

    def test_insert_data(self):
        self.cli.insert_data('some_text')
        self.assertEqual(self.cli.text, 'some_text')
        self.assertEqual(self.cli.cursor_position, len('some_text'))

    def test_mouse_movement(self):
        self.cli.insert_data('some_text')
        self.cli.cursor_left()
        self.cli.cursor_left()
        self.cli.cursor_left()
        self.cli.cursor_right()
        self.cli.insert_data('A')
        self.assertEqual(self.cli.text, 'some_teAxt')
        self.assertEqual(self.cli.cursor_position, len('some_teA'))

    def test_home_end(self):
        self.cli.insert_data('some_text')
        self.cli.home()
        self.cli.insert_data('A')
        self.cli.end()
        self.cli.insert_data('B')
        self.assertEqual(self.cli.text, 'Asome_textB')
        self.assertEqual(self.cli.cursor_position, len('Asome_textB'))

    def test_backspace(self):
        self.cli.insert_data('some_text')
        self.cli.cursor_left()
        self.cli.cursor_left()
        self.cli.backspace()

        self.assertEqual(self.cli.text, 'some_txt')
        self.assertEqual(self.cli.cursor_position, len('some_t'))


if __name__ == '__main__':
    unittest.main()
