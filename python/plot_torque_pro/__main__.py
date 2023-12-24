#!/usr/bin/env python
import logging
import sys
from pathlib import Path

from .config import process_config
from .plot import plot_data


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
    plot_data(config_dict['csv_path'], config_dict)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    main()
