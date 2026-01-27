from prompt_toolkit.document import Document
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.utils import (
    get_cwidth,
    grapheme_cluster_count,
    iter_grapheme_clusters,
)

# Test constants
FAMILY = "\U0001f468\u200d\U0001f469\u200d\U0001f467"  # ZWJ sequence
FLAG = "\U0001f1fa\U0001f1f8"  # Regional indicators
CAFE = "cafe\u0301"  # Combining accent
NINO = "nin\u0303o"  # n + i + n + combining tilde + o = niño


def test_get_cwidth():
    # ASCII
    assert get_cwidth("") == 0
    assert get_cwidth("hello") == 5

    # CJK wide characters
    assert get_cwidth("\u4e2d") == 2
    assert get_cwidth("\u4e2d\u6587") == 4

    # Emoji sequences (ZWJ, flags, skin tones, VS-16)
    assert get_cwidth(FAMILY) == 2
    assert get_cwidth(FLAG) == 2
    assert get_cwidth("\U0001f44b\U0001f3fb") == 2  # skin tone
    assert get_cwidth("\u2764\ufe0f") == 2  # VS-16

    # Combining characters
    assert get_cwidth("e\u0301") == 1
    assert get_cwidth(CAFE) == 4


def test_grapheme_cluster_iteration():
    assert list(iter_grapheme_clusters("hello")) == ["h", "e", "l", "l", "o"]
    assert list(iter_grapheme_clusters(FAMILY)) == [FAMILY]
    assert list(iter_grapheme_clusters(FLAG)) == [FLAG]
    assert list(iter_grapheme_clusters(CAFE)) == ["c", "a", "f", "e\u0301"]


def test_grapheme_cluster_count():
    assert grapheme_cluster_count("hello") == 5
    assert grapheme_cluster_count(FAMILY) == 1
    assert grapheme_cluster_count(CAFE) == 4


def test_cursor_right_grapheme():
    # ASCII unchanged
    assert Document("hello", 0).get_cursor_right_position() == 1
    assert Document("hello", 0).get_cursor_right_position(2) == 2

    # Skips entire grapheme cluster
    assert Document(FAMILY + "x", 0).get_cursor_right_position() == len(FAMILY)
    assert Document(FLAG + "x", 0).get_cursor_right_position() == len(FLAG)

    # At position 3, 'e\u0301' is one grapheme but 2 code points
    assert Document(CAFE, 3).get_cursor_right_position() == 2


def test_cursor_left_grapheme():
    # ASCII unchanged
    assert Document("hello", 5).get_cursor_left_position() == -1
    assert Document("hello", 5).get_cursor_left_position(2) == -2

    # Skips entire grapheme cluster
    assert Document(FAMILY + "x", len(FAMILY)).get_cursor_left_position() == -len(
        FAMILY
    )
    assert Document(FLAG + "x", len(FLAG)).get_cursor_left_position() == -len(FLAG)

    # 'e\u0301' is one grapheme but 2 code points, so -2
    assert Document(CAFE, len(CAFE)).get_cursor_left_position() == -2


def test_current_char_grapheme():
    assert Document(FAMILY + "x", 0).current_char == FAMILY
    assert Document(CAFE, 3).current_char == "e\u0301"  # position 3 = 'e' + accent


def test_current_char_inside_grapheme():
    """Cursor on combining tilde returns full grapheme."""
    assert Document(NINO, 3).current_char == "n\u0303"


def test_current_char_at_end():
    """Cursor at end of text returns empty string."""
    assert Document("hello", 5).current_char == ""
    assert Document("", 0).current_char == ""


def test_char_before_cursor_grapheme():
    assert Document(FAMILY + "x", len(FAMILY)).char_before_cursor == FAMILY
    assert Document(CAFE, len(CAFE)).char_before_cursor == "e\u0301"


def test_char_before_cursor_inside_grapheme():
    """Cursor on combining tilde returns previous grapheme."""
    assert Document(NINO, 3).char_before_cursor == "i"


def test_char_before_cursor_at_start():
    """Cursor at start of text returns empty string."""
    assert Document("hello", 0).char_before_cursor == ""
    assert Document("", 0).char_before_cursor == ""


def test_explode_text_fragments_grapheme():
    # Family emoji should stay as single fragment
    fragments = [("", FAMILY + "x")]
    exploded = explode_text_fragments(fragments)
    assert len(exploded) == 2
    assert exploded[0][1] == FAMILY
    assert exploded[1][1] == "x"

    # Combining accent should stay with base character
    fragments = [("", CAFE)]
    exploded = explode_text_fragments(fragments)
    assert len(exploded) == 4
    assert exploded[3][1] == "e\u0301"

    # Flag should stay as single fragment
    fragments = [("", FLAG + "!")]
    exploded = explode_text_fragments(fragments)
    assert len(exploded) == 2
    assert exploded[0][1] == FLAG
    assert exploded[1][1] == "!"


def test_delete_before_cursor_grapheme():
    from prompt_toolkit.buffer import Buffer

    # Deleting skin tone modifier should delete entire emoji
    WAVE_DARK = "\U0001f44b\U0001f3ff"  # 👋🏿
    buf = Buffer()
    buf.text = WAVE_DARK + "x"
    buf.cursor_position = len(WAVE_DARK)
    deleted = buf.delete_before_cursor(count=1)
    assert deleted == WAVE_DARK
    assert buf.text == "x"

    # Deleting combining accent should delete entire grapheme
    buf.text = CAFE
    buf.cursor_position = len(CAFE)
    deleted = buf.delete_before_cursor(count=1)
    assert deleted == "e\u0301"
    assert buf.text == "caf"


def test_delete_grapheme():
    from prompt_toolkit.buffer import Buffer

    # Forward delete on emoji should delete entire grapheme
    buf = Buffer()
    buf.text = FAMILY + "x"
    buf.cursor_position = 0
    deleted = buf.delete(count=1)
    assert deleted == FAMILY
    assert buf.text == "x"

    # Forward delete on combining character
    buf.text = CAFE
    buf.cursor_position = 3  # Before 'e' + accent
    deleted = buf.delete(count=1)
    assert deleted == "e\u0301"
    assert buf.text == "caf"
