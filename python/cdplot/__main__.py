#!/usr/bin/env python
import logging
import sys
from pathlib import Path
from pyparsing import Word, alphanums

from cdplot.data import load_from_csv
from cdplot.filters import create_data_operators, process_data
from cdplot.plot import render_plot
from .config import process_config, serialize_config, determine_columns

logger = logging.getLogger('cdplot')


class KeyValue:
    MINI_LANGUAGE = Word(alphanums) + "=" + Word(alphanums)

    def __init__(self, key_value_string):
        tokens = self.MINI_LANGUAGE.parse_string(key_value_string)
        self.key = tokens[0]
        self.value = tokens[2] if len(tokens) == 3 else None

    def __iter__(self):
        return iter([self.key, self.value])


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-path', '-f', type=Path, nargs='*')
    parser.add_argument('--config', '-c', type=Path)
    parser.add_argument('--output-path', '-o', type=Path)
    # data config parameters
    parser.add_argument('--session', '-s', type=int)
    parser.add_argument('--columns', nargs='*')
    parser.add_argument('--include', '-i', action='append')
    parser.add_argument('--exclude', '-e', action='append')
    parser.add_argument('--include-pattern', '-I', help='glob pattern for including columns to plot')
    parser.add_argument('--exclude-pattern', '-E', help='glob pattern for excluding columns from the plot')
    parser.add_argument('--default-type')
    parser.add_argument('--dropna', '--drop-na', type=bool, help='pandas.read_csv dropna argument')
    parser.add_argument('--dropna-threshold', '--drop-na-threshold', type=bool, help='pandas.read_csv dropna_threshold argument')
    parser.add_argument('--fillna', '--fill-na', type=bool, help='pandas.read_csv fillna argument')
    # plot config parameters
    parser.add_argument('--x', '-x', help='column to use for the x-axis')
    parser.add_argument('--y', '-y', help='column(s) to use for the y-axis', nargs='*')
    parser.add_argument('--y2', help='column(s) to use for the right y axis', nargs='*')
    parser.add_argument('plot',  nargs='*', type=KeyValue,
                        help='Any additional key-value parameters can be specified after -- separator')
    arguments = parser.parse_args(argv)
    args_dict = dict(vars(arguments))
    args_dict['plot'] = dict(args_dict.pop('plot', {}))

    # Filter out unset parameters
    args_dict = dict(filter(lambda k_v: k_v[1] is not None, args_dict.items()))
    config_path = args_dict.pop('config', None)

    config_dict = process_config(config_path, **args_dict)
    try:
        plot_data(config_dict)
    except Exception:
        logger.error("Plotting failed. Here's the config\n%s", serialize_config(config_dict))
        raise


def plot_data(config: dict):
    csv_data = load_from_csv(config['data'])
    csv_data = augment_data(csv_data, config)
    plot_handle = render_plot(csv_data, config['plot'])

    logger.debug("To reproduce this plot, put the following toml into its own config file\n%s",
                 serialize_config(config))

    if config.get('output_path'):
        plot_handle.write_html(config['output_path'])
        logger.info("Written to %s", str(config['output_path']))
    else:
        plot_handle.show()

    logger.info("done")


def augment_data(csv_data, config):
    """ Augments or updates csv data with any operations specified in the config """
    # Augment data as needed
    operations = list(create_data_operators(config, list(csv_data.columns)))
    process_data(csv_data, operations)

    # Then truncate data as needed
    plot_columns = determine_columns(list(csv_data.columns), config['data'])
    return csv_data[plot_columns].copy()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    main()
