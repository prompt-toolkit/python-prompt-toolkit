from __future__ import unicode_literals
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.search_state import SearchLastWordState

import pytest


@pytest.fixture
def _buffer():
    buf = Buffer()
    buf.insert_text('alpha beta gamma delta\n')
    buf.reset(append_to_history=True)
    buf.insert_text('one two three four\n')
    buf.reset(append_to_history=True)
    return buf


@pytest.fixture
def _search_state():
    return SearchLastWordState()


def test_empty_history(_buffer, _search_state):
    buf = Buffer()
    buf.insert_previous_nth_word(_search_state)
    assert buf.document.current_line == ''


def test_simple_search(_buffer, _search_state):
    _buffer.insert_previous_nth_word(_search_state)
    assert _buffer.document.current_line == 'four'


def test_simple_search_with_quotes(_buffer, _search_state):
    _buffer.insert_text("""one two "three 'x' four"\n""")
    _buffer.reset(append_to_history=True)
    _buffer.insert_previous_nth_word(_search_state)
    assert _buffer.document.current_line == '''"three 'x' four"'''


def test_simple_search_with_arg(_buffer, _search_state):
    _buffer.insert_previous_nth_word(_search_state, word_pos=2)
    assert _buffer.document.current_line == 'three'


def test_simple_search_with_arg_out_of_bounds(_buffer, _search_state):
    _buffer.insert_previous_nth_word(_search_state, word_pos=8)
    assert _buffer.document.current_line == ''


def test_repeated_search(_buffer, _search_state):
    _buffer.insert_previous_nth_word(_search_state)
    _buffer.insert_previous_nth_word(_search_state)
    assert _buffer.document.current_line == 'delta'


def test_repeated_search_with_wraparound(_buffer, _search_state):
    _buffer.insert_previous_nth_word(_search_state)
    _buffer.insert_previous_nth_word(_search_state)
    _buffer.insert_previous_nth_word(_search_state)
    assert _buffer.document.current_line == 'four'
