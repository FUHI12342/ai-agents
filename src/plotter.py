import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot_trend(x, y, trend_x, trend_y, output_path):
    """
    Plot data points and trend line, save as PNG.

    Args:
        x (list or array): X coordinates of data points
        y (list or array): Y coordinates of data points
        trend_x (list or array): X coordinates of trend line
        trend_y (list or array): Y coordinates of trend line
        output_path (str): Path to save the PNG file
    """
    dirpath = os.path.dirname(output_path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    plt.figure(figsize=(10, 6))
    plt.scatter(x, y, label='Data Points', alpha=0.6)
    plt.plot(trend_x, trend_y, color='red', linewidth=2, label='Trend Line')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title('Trend Illustration')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()