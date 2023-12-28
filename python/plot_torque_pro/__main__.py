#!/usr/bin/env python
import logging
import sys
from pathlib import Path

from plot_torque_pro.data import load_from_csv
from plot_torque_pro.plot import render_plot
from .config import process_config, serialize_config

logger = logging.getLogger('plot_torque_pro')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-path', '-f', type=Path)
    parser.add_argument('--config', '-c', type=Path, default='plot_torque_pro.toml')
    parser.add_argument('--include', '-i', action='append')
    parser.add_argument('--exclude', '-e', action='append')
    parser.add_argument('--include-glob', '-g', help='glob pattern for including columns to plot')
    arguments = parser.parse_args()
    args_dict = dict(vars(arguments))

    # Filter out unset parameters
    args_dict = dict(filter(lambda k_v: k_v[1] is not None, args_dict.items()))
    config_path = args_dict.pop('config')

    config_dict = process_config(config_path, **args_dict)
    plot_data(config_dict)


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


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    main()
