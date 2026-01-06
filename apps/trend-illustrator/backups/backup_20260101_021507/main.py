#!/usr/bin/env python3

import argparse
import csv
import sys
import os
from .plotter import plot_trend
from .trend_calculator import calculate_linear_trend

def load_data_from_csv(file_path):
    """
    Load data from CSV file. Assumes first column is x, second is y.
    """
    x = []
    y = []
    try:
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    x.append(float(row[0]))
                    y.append(float(row[1]))
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        sys.exit(1)
    except ValueError as e:
        print(f"Error parsing data: {e}")
        sys.exit(1)

    return np.array(x), np.array(y)

def main():
    parser = argparse.ArgumentParser(description='Trend Illustrator - Plot trends from data')
    parser.add_argument('--input', '-i', required=True, help='Input CSV file path')
    parser.add_argument('--output', '-o', default='trend.png', help='Output plot file path')

    args = parser.parse_args()

    # Load data
    x, y = load_data_from_csv(args.input)

    # Calculate trend
    coeffs, trend_y = calculate_linear_trend(x, y)

    # Plot and save
    plot_trend(x, y, x, trend_y, args.output)

    print(f"Trend calculated with slope: {coeffs[0]:.4f}, intercept: {coeffs[1]:.4f}")

if __name__ == '__main__':
    main()