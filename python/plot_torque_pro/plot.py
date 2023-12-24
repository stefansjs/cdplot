"""
Reads and plots data from csv
"""
import logging
import re
import tempfile
from collections import defaultdict
from pathlib import Path

import pandas
import plotly.express

from .config import determine_columns, serialize_config

logger = logging.getLogger(__name__)


def plot_data(csv_path: Path, config: dict):
    csv_data = load_from_csv(csv_path, config)
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
