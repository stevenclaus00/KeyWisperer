import pytest

from keywhisperer.contracts import (
    CommandSpec, FormatOptions, PressKeys, SetListening, TypeText, UndoLast,
)
from keywhisperer.text import DefaultTextProcessor, build_processor

P = build_processor({})


@pytest.mark.parametrize("utt,expected", [
    ("Send it.", [PressKeys(["enter"])]),
    ("send", [PressKeys(["enter"])]),
    ("Send message!", [PressKeys(["enter"])]),
    ("New line.", [PressKeys(["shift", "enter"])]),
    ("New paragraph", [PressKeys(["shift", "enter"], repeat=2)]),
    ("Scratch that.", [UndoLast()]),
    ("delete that", [UndoLast()]),
    ("Select all.", [PressKeys(["ctrl", "a"])]),
    ("Copy that", [PressKeys(["ctrl", "c"])]),
    ("Paste.", [PressKeys(["ctrl", "v"])]),
    ("paste that", [PressKeys(["ctrl", "v"])]),
    ("Undo.", [PressKeys(["ctrl", "z"])]),
    ("Press enter", [PressKeys(["enter"])]),
    ("Press tab.", [PressKeys(["tab"])]),
    ("press escape", [PressKeys(["escape"])]),
    ("Backspace.", [PressKeys(["backspace"])]),
    ("Stop listening.", [SetListening(False)]),
    ("start listening", [SetListening(True)]),
])
def test_whole_utterance_commands(utt, expected):
    assert P.process(utt, "Hello") == expected


def test_trailing_send():
    assert P.process("That's all, send it.", "") == [
        TypeText("That's all"), PressKeys(["enter"]),
    ]
    assert P.process("Please fix the bug. Send message.", "Hi.") == [
        TypeText(" Please fix the bug."), PressKeys(["enter"]),
    ]


@pytest.mark.parametrize("utt", [
    "please copy that file",
    "I need to send it to Bob tomorrow",
    "we should undo the change",
    "you can paste the text here",
    "I want a new line of products",
    "resend",
])
def test_no_false_triggers(utt):
    actions = P.process(utt, "")
    assert len(actions) == 1 and isinstance(actions[0], TypeText)


def test_non_send_command_not_trailing():
    out = P.process("let me select all", "")
    assert out == [TypeText("Let me select all")]


def test_plain_text_joined_and_formatted():
    assert P.process("hello world", "") == [TypeText("Hello world")]
    assert P.process("and then twenty five", "Hello") == [TypeText(" and then 25")]
    assert P.process("it works. really", "Done.") == [TypeText(" It works. Really")]


@pytest.mark.parametrize("utt", ["", "   ", ".", "...", "?!", "Um.", "uh,"])
def test_empty_like(utt):
    assert P.process(utt, "x") == []


@pytest.mark.parametrize("utt", ["Thank you.", "Thanks for watching!", "you", "Bye."])
def test_hallucinations_dropped(utt):
    assert P.process(utt, "") == []


def test_hallucination_only_when_entire_utterance():
    assert P.process("Thank you for the help.", "") == [TypeText("Thank you for the help.")]


def test_hallucination_list_configurable():
    p = build_processor({"hallucinations": []})
    assert p.process("Thank you.", "") == [TypeText("Thank you.")]
    p = build_processor({"hallucinations": ["okay then"]})
    assert p.process("Okay then.", "") == []


def test_filler_before_command():
    assert P.process("Um, send it.", "") == [PressKeys(["enter"])]


def test_user_commands_added():
    p = build_processor({"commands": [
        {"phrases": ["sign off"], "actions": [
            {"type": "text", "text": "Best regards"},
            {"type": "keys", "keys": ["ctrl", "Enter"]},
        ]},
        {"phrases": ["go quiet"], "actions": [{"type": "listening", "value": False}]},
        {"phrases": ["oops"], "actions": [{"type": "undo"}]},
    ]})
    assert p.process("Sign off.", "") == [TypeText("Best regards"), PressKeys(["ctrl", "enter"])]
    assert p.process("go quiet", "") == [SetListening(False)]
    assert p.process("oops", "") == [UndoLast()]
    assert p.process("send it", "") == [PressKeys(["enter"])]  # defaults remain


def test_user_command_overrides_default():
    p = build_processor({"commands": [
        {"phrases": ["new line"], "actions": [{"type": "keys", "keys": ["enter"]}]},
        {"phrases": ["send it"], "actions": [{"type": "keys", "keys": ["ctrl", "enter"], "repeat": 1}]},
    ]})
    assert p.process("new line", "") == [PressKeys(["enter"])]
    assert p.process("ok, send it", "") == [TypeText("Ok"), PressKeys(["ctrl", "enter"])]


def test_build_processor_format_options():
    p = build_processor({"format": {"number_formatting": False, "auto_capitalize": False}})
    assert p.process("twenty five", "") == [TypeText("twenty five")]


def test_build_processor_errors():
    with pytest.raises(ValueError):
        build_processor({"format": {"bogus": 1}})
    with pytest.raises(ValueError):
        build_processor({"commands": [{"phrases": ["x"], "actions": [{"type": "nope"}]}]})


def test_returned_actions_are_copies():
    a = P.process("send it", "")
    a[0].keys.append("x")
    assert P.process("send it", "") == [PressKeys(["enter"])]


def test_direct_construction():
    p = DefaultTextProcessor(FormatOptions(), [CommandSpec(["hi there"], [UndoLast()])])
    assert p.process("Hi there!", "") == [UndoLast()]
