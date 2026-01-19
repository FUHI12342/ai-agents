import matplotlib.pyplot as plt
import numpy as np

def plot_trend(x, y, trend_x, trend_y, output_file):
    """
    Plot data points and trend line, save to file.
    """
    plt.figure(figsize=(10, 6))
    plt.scatter(x, y, label='Data points', color='blue')
    plt.plot(trend_x, trend_y, label='Trend line', color='red', linewidth=2)
    plt.xlabel('X values')
    plt.ylabel('Y values')
    plt.title('Trend Illustration')
    plt.legend()
    plt.grid(True)
    plt.savefig(output_file)
    plt.close()
    print(f"Plot saved to {output_file}")