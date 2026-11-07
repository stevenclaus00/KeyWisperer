import pytest

from keywhisperer.text.formatting import (
    apply_smart_quotes,
    capitalize_sentences,
    convert_spoken_numbers,
    format_text,
    join,
    remove_fillers,
)


@pytest.mark.parametrize("src,expected", [
    ("twenty five", "25"),
    ("twenty-five apples", "25 apples"),
    ("thirty", "30"),
    ("fifteen minutes", "15 minutes"),
    ("one hundred", "100"),
    ("two hundred and five", "205"),
    ("three hundred and twenty five", "325"),
    ("one hundred twenty", "120"),
    ("one of the best", "one of the best"),
    ("I have two cats", "I have two cats"),
    ("someone", "someone"),
])
def test_numbers(src, expected):
    assert convert_spoken_numbers(src) == expected


def test_capitalize_sentences():
    assert capitalize_sentences("hello. how are you? fine! ok") == "hello. How are you? Fine! Ok"


def test_smart_quotes():
    assert apply_smart_quotes('he said "hi"') == "he said “hi”"
    assert apply_smart_quotes("don't go") == "don't go"
    assert apply_smart_quotes("the 'big' one") == "the ‘big’ one"


@pytest.mark.parametrize("src,expected", [
    ("Um, hello there", "hello there"),
    ("I think, uh, we should", "I think, we should"),
    ("so um yes", "so yes"),
    ("yes uhh.", "yes."),
    ("uh-huh sure", "uh-huh sure"),
    ("umbrella", "umbrella"),
    ("Erm, well", "well"),
])
def test_fillers(src, expected):
    assert remove_fillers(src) == expected


def test_join_empty_previous_capitalizes():
    assert join("", "hello world") == "Hello world"


@pytest.mark.parametrize("prev", ["Done.", "Done!", "Done?", "line\n", "Done. "])
def test_join_after_sentence_end(prev):
    out = join(prev, "next thing")
    assert out.lstrip() == "Next thing"


def test_join_spacing():
    assert join("Hello", "world") == " world"  # never lowercases/capitalizes mid-sentence
    assert join("Hello ", "world") == "world"
    assert join("Done.\n", "Next") == "Next"
    assert join("Done.", "next") == " Next"


def test_join_never_lowercases():
    assert join("Hello", "World") == " World"


def test_join_no_capitalize_option():
    assert join("", "hello", capitalize=False) == "hello"


def test_join_empty_new():
    assert join("abc", "  ") == ""


def test_format_text_options():
    assert format_text("um twenty five. next", smart_quotes=False) == "25. Next"
    assert format_text("twenty five", number_formatting=False) == "twenty five"
    assert format_text("a. b", auto_capitalize=False) == "a. b"
