"""Reading on demand (atlas/agent/text.py): the corrigendum is applied by code and the gate holds. No network."""
from atlas.agent import text
from atlas.corpus.chunker import load


def _piece(source: str, locator: str):
    return next(c for c in load() if c.source == source and c.locator == locator)


def test_the_corrigendum_is_applied_to_the_text_read():
    shown, mark = text.corrected(_piece("REG", "Art. 53(1)"))
    assert "20 July 2028" in shown and "14 July 2028" not in shown
    assert "14 July 2028" in mark and "Corrigendum, point 8" in mark


def test_a_piece_the_corrigendum_does_not_touch_is_left_alone():
    piece = _piece("REG", "Art. 53(1)")
    other = next(c for c in load() if c.source == "REG" and c.locator.startswith("Art. 2("))
    assert text.corrected(other) == (other.text, "")
    assert text.corrected(piece)[0] != piece.text


def test_no_quote_no_answer():
    piece = _piece("REG", "Art. 53(1)")
    shown = [(piece, text.corrected(piece)[0], "")]
    real = "By 20 July 2028 and every four years thereafter, the Commission shall submit a report"
    held, why = text.check("date", "2028-07-20", [{"passage": 0, "quote": real}], shown)
    assert held and not why
    # a sentence that is not in the passage
    assert text.check("date", "2028-07-20", [{"passage": 0, "quote": "The Commission reports by 20 July 2028 at the latest"}], shown)[0] == []
    # a date that the sentence pointed at does not carry
    assert text.check("date", "2029-07-20", [{"passage": 0, "quote": real}], shown)[0] == []
    # a period that the sentence pointed at does not carry
    assert text.check("duration", "P7Y", [{"passage": 0, "quote": real}], shown)[0] == []
    assert text.check("duration", "P4Y", [{"passage": 0, "quote": real}], shown)[0]
