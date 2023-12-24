"""
Reads and plots data from csv
"""
import logging
import re
import tempfile
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


def load_from_csv(csv_path, config):
    conf = config['data']
    read_args = dict(skipinitialspace=True, parse_dates=True, index_col=conf['index'])

    # Split the data into multiple CSVs if necessary
    sessions, tempdir = preprocess_data(csv_path)

    if config['plot'].get('session'):
        csv_dataframe = pandas.read_csv(sessions[config['plot']['session']], **read_args)
    elif len(sessions) == 1:
        csv_dataframe = pandas.read_csv(sessions[0], **read_args)
    else:
        all_dataframes = [pandas.read_csv(f, **read_args) for f in sessions]
        csv_dataframe = pandas.concat(all_dataframes)

    plot_columns = determine_columns(list(csv_dataframe.columns), config)
    csv_dataframe = csv_dataframe[plot_columns].copy()

    return csv_dataframe


def render_plot(csv_data, config):
    return plotly.express.line(csv_data, x=config['x'], y=config['y'])


def preprocess_data(csv_path):
    header_indices = []
    with csv_path.open() as fh:
        for index, line in enumerate(fh):
            has_numeric = re.search(r'(,\s?[\d\.\+-],)+', line)
            if has_numeric is None:
                header_indices.append(index)

    if len(header_indices) == 1:
        return [csv_path], None

    # split the file into multiple files
    return split_csv(csv_path, split_indices=header_indices + [index+1])


def split_csv(csv_path, split_indices):
    split_indices = split_indices[1:] if split_indices[0] == 0 else split_indices

    temp_dir = Path(tempfile.mkdtemp(prefix='plot_torque_pro'))

    with csv_path.open() as fh:
        output_iter = iter(_next_file(split_indices, temp_dir))
        output_handle, next_index = next(output_iter)

        try:
            split_paths = [Path(output_handle.name)]

            for index, line in enumerate(fh):
                if index >= next_index:
                    # rotate the file
                    output_handle, next_index = next(output_iter)
                    split_paths.append(Path(output_handle.name))

                output_handle.write(line)

        except IOError:
            output_handle.close()
            for f in split_paths:
                f.unlink(missing_ok=True)
            temp_dir.rmdir()
            raise

    return split_paths, temp_dir


def _next_file(indices, dest_dir):
    dest_path = Path(dest_dir)

    output_path = dest_path / f'session_0.csv'
    for session_id, next_index in enumerate(indices):
        output_handle = output_path.open('wt')
        yield output_handle, next_index

        output_handle.close()
        output_path = dest_path / f'session_{session_id+1}.csv'
