from __future__ import unicode_literals

from prompt_toolkit.widgets import RadioList

import pytest

def test_initial():
    values = [
                (1, 'some_text'),
                ('fizz', 'some_more_text'),
                ({'foo':'bar'}, 'even_more_text')
             ]
    radiolist = RadioList(values)
    assert radiolist.current_value == 1
    assert radiolist._selected_index == 0

def test_default():
    values = [
                (1, 'some_text'),
                ('fizz', 'some_more_text'),
                ({'foo':'bar'}, 'even_more_text')
             ]
    radiolist = RadioList(values, 1)
    assert radiolist.current_value == 'fizz'
    assert radiolist._selected_index == 1

def test_bad_params():
    with pytest.raises(AssertionError):
        radiolist = RadioList([])

    with pytest.raises(AssertionError):
        radiolist = RadioList(None)

    with pytest.raises(AssertionError):
        values = (
                    (1, 'some_text'),
                    ('fizz', 'some_more_text'),
                    ({'foo':'bar'}, 'even_more_text')
                 )
        radiolist = RadioList(values)

    with pytest.raises(AssertionError):
        values = [
                    (1, 'some_text', 'whoops'),
                    ('fizz', 'some_more_text'),
                    ({'foo':'bar'}, 'even_more_text')
                 ]
        radiolist = RadioList(values)

    with pytest.raises(AssertionError):
        values = [
                    (1, 'some_text'),
                    ('fizz', ),
                    ({'foo':'bar'}, 'even_more_text')
                 ]
        radiolist = RadioList(values)

    with pytest.raises(AssertionError):
        values = [
                    (1, 'some_text'),
                    ('fizz', 'some_more_text'),
                    [{'foo':'bar'}, 'even_more_text']
                 ]
        radiolist = RadioList(values)

    with pytest.raises(AssertionError):
        values = [
                    (1, 'some_text'),
                    ('fizz', 'some_more_text'),
                    ({'foo':'bar'}, 'even_more_text')
                 ]
        radiolist = RadioList(values, 3)

    with pytest.raises(AssertionError):
        values = [
                    (1, 'some_text'),
                    ('fizz', 'some_more_text'),
                    ({'foo':'bar'}, 'even_more_text')
                 ]
        radiolist = RadioList(values, -1)

    with pytest.raises(AssertionError):
        values = [
                    (1, 'some_text'),
                    ('fizz', 'some_more_text'),
                    ({'foo':'bar'}, 'even_more_text')
                 ]
        radiolist = RadioList(values, None)

    with pytest.raises(AssertionError):
        values = [
                    (1, 'some_text'),
                    ('fizz', 'some_more_text'),
                    ({'foo':'bar'}, 'even_more_text')
                 ]
        radiolist = RadioList(values, 'whoops')
