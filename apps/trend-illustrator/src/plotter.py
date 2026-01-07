import matplotlib.pyplot as plt

def plot_trend(x, y, trend_x, trend_y, output_file):
    plt.figure()
    plt.plot(x, y, label='Data')
    plt.plot(trend_x, trend_y, label='Trend', linestyle='--')
    plt.legend()
    plt.savefig(output_file)
    plt.close()