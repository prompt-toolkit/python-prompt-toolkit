from prompt_toolkit.styles.defaults import default_ui_style


def test_selected_fuzzy_completion_outside_colors() -> None:
    attrs = default_ui_style().get_attrs_for_style_str(
        "class:completion-menu.completion.current class:fuzzymatch.outside"
    )

    # Reverse makes the foreground the background: it must not depend on the
    # terminal foreground, which can be white like the selected text.
    assert attrs.color == "444444"
    assert attrs.bgcolor == "ffffff"
    assert attrs.reverse
