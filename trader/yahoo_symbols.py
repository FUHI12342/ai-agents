def symbol_to_yahoo_file_stem(symbol: str) -> str:
    """
    Convert a Yahoo Finance symbol to the corresponding file stem for CSV files.

    Examples:
    - ^N225 -> N225
    - ^GSPC -> GSPC
    - USDJPY=X -> USDJPY_X
    """
    stem = symbol.replace('^', '').replace('=X', '_X')
    return stem