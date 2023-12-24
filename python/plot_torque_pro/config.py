"""
Handles reading config files and arguments to produce one config dictionary
"""
import fnmatch
import logging
from pathlib import Path

import jsonschema
import toml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'csv_path': None,
    'output_path': None,
    'session': None,

    'data': {
        'include': [],
        'exclude': [],
        'include_pattern': [],
        'exclude_pattern': [],
    },
    'plot': {
        'x_axis': 'Device Time',
    },
}

STRING_ARRAY_SCHEMA = {'type': 'array', 'items': {'type': 'string'}}
TOML_SCHEMA = {
    'type': 'object',
    'properties': dict(
        plot_torque_pro={
            'type': 'object',
            'properties': dict(
                csv_path={'type': 'string'},
                output_path={'type': 'string'},
                session={'type': 'number'},
                data={
                    'type': 'object',
                    'properties': dict(
                        columns=STRING_ARRAY_SCHEMA,
                        include=STRING_ARRAY_SCHEMA,
                        exclude=STRING_ARRAY_SCHEMA,
                        include_pattern=STRING_ARRAY_SCHEMA,
                        exclude_pattern=STRING_ARRAY_SCHEMA,
                    )
                },
                plot={
                    'type': 'object',
                    'properties': dict(

                    )
                }
            ),
        }
    ),
    'requiredProperties': ['plot_torque_pro']
}


def lfilter(*args):
    return list(filter(*args))


def process_config(config_file=None, **config_args):
    if config_file is None and not config_args:
        # base case
        return DEFAULT_CONFIG

    config = dict(DEFAULT_CONFIG)

    if config_file is not None:
        config_from_toml = toml.load(config_file)
        jsonschema.validate(config_from_toml, TOML_SCHEMA)
        config = merge_configs(config, config_from_toml['plot_torque_pro'])

    # command-line arguments should override the config file(s)
    config = merge_configs(config, config_overrides)

    # mutate parameters as needed
    normalize_config(config)
    return config


def merge_configs(config, overrides, parent_name=None):
    # this method should probably take a strategy of some kind
    merged_config = dict(config)

    for key, value in overrides.items():
        if key not in merged_config or merged_config[key] is None:
            merged_config[key] = value

        nested_name = key if parent_name is None else f'{parent_name}.{key}'

        if isinstance(value, dict):
            merged_config[key] = merge_configs(merged_config[key], value, parent_name=nested_name)

        elif isinstance(value, list):
            merged_config[key] += value

        else:
            merged_config[key] = value

    return merged_config


def normalize_config(config):
    """ Make sure that every parameter is of the type expected """

    # update paths to be a Path instance
    config['csv_path'] = Path(config['csv_path']).expanduser()
    if config.get('output_path'):
        config['output_path'] = Path(config['output_path']).expanduser()


def determine_columns(columns, config):
    included_columns = None

    if config.get('include'):
        include_set = set(config['include'])
        included_columns = lfilter(lambda c: c in include_set, columns)
        del config['include']

    if config.get('include_pattern'):
        included_columns = included_columns or []
        for pattern in config['include_pattern']:
            included_columns.extend(fnmatch.filter(columns, pattern))
        del config['include_pattern']

    if included_columns is not None:
        columns = included_columns

    if config.get('exclude'):
        exclude_set = set(config['exclude'])
        columns = lfilter(lambda c: c not in exclude_set, columns)
        del config['exclude']

    if config.get('exclude_pattern'):
        for pattern in config['exclude_pattern']:
            columns = lfilter(lambda c: not fnmatch.fnmatch(c, pattern), columns)
        del config['exclude_pattern']

    config['columns'] = columns

    return columns
