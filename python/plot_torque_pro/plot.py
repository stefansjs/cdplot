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
    csv_data = _prune_dataframe(csv_data, config)
    plot_handle = render_plot(csv_data, config['plot'])

    logger.debug("To reproduce this plot, put the following toml into its own config file\n%s",
                 serialize_config(config))

    if config.get('output_path'):
        plot_handle.write_to_file(config['output_path'])
    else:
        plot_handle.show()

    logger.info("done")


def render_plot(csv_data, config):
    return plotly.express.line(csv_data, x=config['x'], y=config['y'])


def _prune_dataframe(csv_dataframe, config):
    plot_columns = determine_columns(list(csv_dataframe.columns), config)
    return csv_dataframe[plot_columns].copy()
