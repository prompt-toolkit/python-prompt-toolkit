from prompt_toolkit.formatted_text import fragment_list_to_text
from prompt_toolkit.layout import to_window
from prompt_toolkit.widgets import Button


class TestButton:
    def _to_text(self, button: Button) -> str:
        control = to_window(button).content
        return fragment_list_to_text(control.text())

    def test_defaulf_button(self):
        button = Button("Exit")
        assert self._to_text(button) == "<   Exit   >"

    def test_custom_button(self):
        button = Button("Exit", left_char="[", right_char="]")
        assert self._to_text(button) == "[   Exit   ]"
