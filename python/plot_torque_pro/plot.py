"""
Reads and plots data from csv
"""
import logging

import plotly.express

from .config import serialize_config, determine_columns
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
    csv_data = _select_data(csv_data, config)
    return plotly.express.line(csv_data, x=config['x'], y=config['y'])


def _select_data(csv_dataframe, config):
    plot_columns = determine_columns(list(csv_dataframe.columns), config)

    # Make sure we handle the x-axis
    x_axis = config.get('x')
    if x_axis is not None and x_axis not in plot_columns:
        config['y'] = plot_columns
        plot_columns.insert(0, x_axis)
    elif x_axis is not None and x_axis in plot_columns:
        config['y'] = list(plot_columns)
        config['y'].remove(x_axis)
    elif plot_columns:
        config['x'] = plot_columns[0]
        config['y'] = plot_columns[1:]

    return csv_dataframe[plot_columns].copy()
