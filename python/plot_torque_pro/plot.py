"""
Reads and plots data from csv
"""
import logging
from pathlib import Path

import pandas

from .config import determine_columns, serialize_config

logger = logging.getLogger(__name__)


def plot_data(csv_path: Path, config: dict):
    csv_data = load_from_csv(csv_path, config['data'])
    plot_handle = render_plot(csv_data, config['plot'])

    logger.debug("To reproduce this plot, put the following toml into its own config file\n%s",
                 serialize_config(config))

    if config.get('output_path'):
        plot_handle.write_to_file(config['output_path'])
    else:
        plot_handle.show()

    logger.info("done")


def load_from_csv(csv_path, config):
    csv_dataframe = pandas.read_csv(csv_path)
    plot_columns = determine_columns(list(csv_dataframe.columns), config)
    csv_dataframe = csv_dataframe[plot_columns].copy()

    return csv_dataframe


def render_plot(csv_data, param):
    pass
