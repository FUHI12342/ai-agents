import pytest
from pathlib import Path
import importlib.util

def _load_main():
    path = Path(__file__).resolve().parents[1] / "src" / "main.py"
    spec = importlib.util.spec_from_file_location("char_card_manager_main", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

_main = _load_main()
create_character_card = _main.create_character_card
list_character_cards = _main.list_character_cards

def test_create_character_card():
    # Test creating a character card
    card = create_character_card("Alice", "A brave adventurer")
    assert card["name"] == "Alice"
    assert card["description"] == "A brave adventurer"

def test_list_character_cards():
    # Test listing character cards
    cards = list_character_cards()
    assert isinstance(cards, list)