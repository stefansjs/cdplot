"""
Handles reading config files and arguments to produce one config dictionary
"""
import datetime
import fnmatch
import logging
from collections import OrderedDict
from pathlib import Path

import jsonschema
import pandas
import plotly
import toml

from plot_torque_pro.functional import lfilter, lchain

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'output_path': None,

    'data': {
        'csv_path': None,
        'session': None,
        'include': [],
        'exclude': [],
        'include_pattern': [],
        'exclude_pattern': [],
        'require': [],
        'index': None,
        'skipinitialspace': True,
        'parse_dates': True,
    },
    'plot': {

    },
}

STRING_ARRAY_SCHEMA = {'type': 'array', 'items': {'type': 'string'}}
TOML_SCHEMA = {
    'type': 'object',
    'properties': dict(
        plot_torque_pro={
            'type': 'object',
            'properties': dict(
                output_path={'type': 'string'},
                data={
                    'description': "Parameters relating to how data should be read from csv",
                    'type': 'object',
                    'properties': dict(
                        csv_path={'type': 'string'},
                        session={'type': 'number'},

                        index={'anyOf': [
                            dict(type='boolean'),  # default = False
                            dict(type='string'),   # one or more column names
                            dict(type='array', items={'type': 'string'}),
                        ]},
                        columns=STRING_ARRAY_SCHEMA,
                        include=STRING_ARRAY_SCHEMA,
                        exclude=STRING_ARRAY_SCHEMA,
                        include_pattern=STRING_ARRAY_SCHEMA,
                        exclude_pattern=STRING_ARRAY_SCHEMA,

                        default_type={'type': 'string'},
                        dtype={
                            'type': 'object',
                            'patternProperties': {
                                "": {'type': 'string'}
                            }
                        },

                        skipinitialspace={'type': 'boolean'},
                        parse_dates={"anyOf": [
                            {'type': 'boolean'},
                            {'type': 'object'},
                            {'type': 'array', 'items': {'type': 'string'}},
                        ]},
                        date_format={'type': 'string'},
                        filters={
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': dict(
                                    source={'type': 'string'},
                                    destination={'type': 'string'},
                                    type={'type': 'string'},
                                ),
                                'requiredProperties': ['source', 'type']
                            }
                        },
                    )
                },
                plot={
                    'description': "Generally how data should be displayed",
                    'type': 'object',
                    'properties': dict(
                        x={'type': 'string'},
                        y=STRING_ARRAY_SCHEMA,
                        y2=STRING_ARRAY_SCHEMA,
                    )
                }
            ),
        }
    ),
    'requiredProperties': ['plot_torque_pro']
}


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
    config_overrides = args_to_config(config_args)
    config = merge_configs(config, config_overrides)

    # mutate parameters as needed
    normalize_config(config)
    return config


def args_to_config(argparse_args):
    data_keys = TOML_SCHEMA['properties']['plot_torque_pro']['properties']['data']['properties'].keys()
    plot_keys = TOML_SCHEMA['properties']['plot_torque_pro']['properties']['plot']['properties'].keys()
    root_keys = TOML_SCHEMA['properties']['plot_torque_pro']['properties'].keys()

    data_dict = {key: value for key, value in argparse_args.items() if key in data_keys}
    plot_dict = {key: value for key, value in argparse_args.items() if key in plot_keys}

    args_config = {key: value for key, value in argparse_args.items() if key in root_keys}
    if data_dict:
        args_config['data'] = data_dict
    if plot_dict:
        args_config['plot'] = plot_dict

    return args_config


def merge_configs(config, overrides, parent_name='plot_torque_pro'):
    # this method should probably take a strategy of some kind
    merged_config = dict(config)

    for key, value in overrides.items():
        if key not in merged_config or merged_config[key] is None:
            merged_config[key] = value
            continue

        nested_name = key if parent_name is None else f'{parent_name}.{key}'

        if isinstance(value, dict):
            merged_config[key] = merge_configs(merged_config[key], value, parent_name=nested_name)

        elif isinstance(value, list) and isinstance(merged_config[key], list):
            merged_config[key] = list(merged_config[key]) + value

        else:
            merged_config[key] = value

    return merged_config


def normalize_config(config):
    """
    Modifies the config in-place to handle any differences between toml parameters and implementation requirements
    """

    # update paths to be a Path instance
    config['data']['csv_path'] = Path(config['data']['csv_path']).expanduser()
    if config.get('output_path'):
        config['output_path'] = Path(config['output_path']).expanduser()

    # Let's also do any needed data augmentation here
    if config['plot'].get('x'):
        config['data']['require'].insert(0, config['plot']['x'])


def serialize_config(config):
    _add_metadata(config)
    toml_config = dict(plot_torque_pro=config)
    return toml.dumps(toml_config, toml.TomlPathlibEncoder(OrderedDict))


def _add_metadata(config):
    if '_metadata' not in config:
        config['_metadata'] = {}

    from plot_torque_pro import __version__
    config['_metadata'].update(
        rendered=datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat(),
        versions={
            'plot_torque_pro': __version__,
            'plotly': plotly.__version__,
            'pandas': pandas.__version__,
        }
    )


def determine_columns(columns, data_config):
    if data_config.get('columns'):
        return data_config['columns']

    included_columns = None

    # deal with include patterns
    if data_config.get('include_pattern'):
        included_columns = lchain(*[fnmatch.filter(columns, pattern) for pattern in data_config['include_pattern']])
    data_config.pop('include_pattern', None)

    # followed by includes
    if data_config.get('include'):
        included_columns = included_columns or []
        include_set = set(data_config['include'])
        existing_set = set(included_columns)
        included_columns.extend(filter(lambda c: c in include_set and c not in existing_set, columns))

        missing_columns = set(filter(lambda c: c not in set(included_columns), data_config['include']))
        if missing_columns:
            logger.warning("Some columns were requested in plot_torque_pro.data.include but are not in the csv: %s",
                           missing_columns)
    data_config.pop('include', None)

    # after all includes handle exclude patterns
    if data_config.get('exclude_pattern'):
        included_columns = included_columns or columns
        for pattern in data_config['exclude_pattern']:
            included_columns = lfilter(lambda c: not fnmatch.fnmatch(c, pattern), included_columns)
    data_config.pop('exclude_pattern', None)

    # followed by excludes
    if data_config.get('exclude'):
        included_columns = included_columns or columns
        exclude_set = set(data_config['exclude'])
        included_columns = lfilter(lambda c: c not in exclude_set, included_columns)
    data_config.pop('exclude', None)

    # finally add back any required columns that weren't included so far
    if data_config.get('require') and included_columns is not None:
        included_columns.extend(filter(lambda c: c not in included_columns, data_config['require']))

        missing_columns = set(filter(lambda c: c not in set(included_columns), data_config['require']))
        if missing_columns:
            logger.error("The following required columns are not available: %s", missing_columns)
            raise ValueError("Some columns were listed as required but they are not available in the csv")
    data_config.pop('require', None)


    # Make the filter operations stable
    if included_columns is not None:
        columns = lfilter(lambda c: c in set(included_columns), columns)

    # update config with the final decision
    data_config['columns'] = columns

    return columns
