#!/usr/bin/env python3
"""
NetDefender - Network Defense and Audit Tool

A minimal CLI tool for detecting differences in network logs and snapshots.
"""

import sys
import os
import argparse
import difflib
from pathlib import Path


def read_file_lines(file_path):
    """Read file and return lines, handling encoding issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except UnicodeDecodeError:
        # Fallback to latin-1 for binary-like files
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.readlines()


def compare_files(file1, file2, output_file=None):
    """Compare two files and show differences."""
    if not os.path.exists(file1):
        print(f"Error: {file1} does not exist")
        return False

    if not os.path.exists(file2):
        print(f"Error: {file2} does not exist")
        return False

    lines1 = read_file_lines(file1)
    lines2 = read_file_lines(file2)

    diff = list(difflib.unified_diff(
        lines1, lines2,
        fromfile=file1, tofile=file2,
        lineterm='', n=3
    ))

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(diff)
        print(f"Differences written to {output_file}")
    else:
        if diff:
            print("Differences found:")
            for line in diff:
                print(line, end='')
        else:
            print("No differences found.")

    return len(diff) == 0


def main():
    parser = argparse.ArgumentParser(
        description="NetDefender - Network log diff detection tool"
    )
    parser.add_argument(
        'file1', help='First file to compare'
    )
    parser.add_argument(
        'file2', help='Second file to compare'
    )
    parser.add_argument(
        '-o', '--output', help='Output file for differences'
    )

    args = parser.parse_args()

    if not compare_files(args.file1, args.file2, args.output):
        sys.exit(1)


if __name__ == '__main__':
    main()