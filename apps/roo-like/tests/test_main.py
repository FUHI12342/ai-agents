import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import main

def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert "Hello from roo-like app!" in captured.out