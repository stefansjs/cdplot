"""
Reads and plots data from csv
"""
import logging

import plotly.express

from .config import serialize_config
from .data import load_from_csv

logger = logging.getLogger(__name__)


def plot_data(config: dict):
    csv_data = load_from_csv(config['data'])
    plot_handle = render_plot(csv_data, config['plot'])

    logger.debug("To reproduce this plot, put the following toml into its own config file\n%s",
                 serialize_config(config))

    if config.get('output_path'):
        plot_handle.write_html(config['output_path'])
        logger.info("Written to %s", str(config['output_path']))
    else:
        plot_handle.show()

    logger.info("done")


def render_plot(csv_data, config):
    layout_data(csv_data, config)
    return plotly.express.line(csv_data, x=config['x'], y=config['y'])


def layout_data(csv_dataframe, config):
    plot_columns = list(csv_dataframe.columns)

    # Make sure we handle the x-axis
    x_axis = config.get('x')
    y_axis = config.get('y')
    y2_axis = config.get('y2')

    if x_axis is not None and x_axis in plot_columns:
        config['y'] = list(plot_columns)
        config['y'].remove(x_axis)
    elif plot_columns:
        config['x'] = plot_columns[0]
        config['y'] = plot_columns[1:]
