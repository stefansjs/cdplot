"""
Reads and plots data from csv
"""
import logging
import re
import tempfile
from collections import defaultdict
from pathlib import Path

import pandas

logger = logging.getLogger(__name__)


def load_from_csv(config):
    csv_path = config['csv_path']

    if config.get('default_type'):
        dtypes = defaultdict(lambda: config['default_type'])
        dtypes.update(config.get('dtype', {}))
    elif config.get('dtype'):
        dtypes = config['dtype']
    else:
        dtypes = None

    read_args = dict(skipinitialspace=config['skipinitialspace'],
                     parse_dates=config['parse_dates'],
                     date_format=config.get('date_format'),
                     index_col=config['index'],
                     dtype=dtypes)

    # Split the data into multiple CSVs if necessary
    with preprocess_data(csv_path) as sessions:
        if config.get('session'):
            csv_dataframe = pandas.read_csv(sessions[config['session']], **read_args)
        elif len(sessions) == 1:
            csv_dataframe = pandas.read_csv(sessions[0], **read_args)
        else:
            all_dataframes = [pandas.read_csv(f, **read_args) for f in sessions]
            csv_dataframe = pandas.concat(all_dataframes)

    return csv_dataframe


def preprocess_data(csv_path):
    header_indices = []
    with csv_path.open() as fh:
        for index, line in enumerate(fh):
            has_numeric = re.search(r'(,\s?[\d\.\+-],)+', line)
            if has_numeric is None:
                logger.debug("session %d = %s", len(header_indices), line.strip())
                header_indices.append(index)

    if len(header_indices) == 1:
        return TemporaryCSV([csv_path])

    # split the file into multiple files
    csv_paths, tempdir = split_csv(csv_path, split_indices=header_indices + [index+1])
    # and wrap the temporary files in a context manager for deleting the files when done
    managed_csvs = TemporaryCSV(csv_paths, tempdir)
    return managed_csvs


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

                output_handle.write(fix_torque_data(line))

        except IOError:
            output_handle.close()
            _cleanup_tmp(split_paths, temp_dir)
            raise

    return split_paths, temp_dir


def fix_torque_data(csv_line):
    return re.sub('∞', 'inf', csv_line)


class TemporaryCSV:
    def __init__(self, csv_paths, temp_dir=None):
        self.csv_paths = csv_paths
        self.temp_dir = temp_dir

    def __enter__(self):
        return self.csv_paths

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir is not None:
            _cleanup_tmp(self.csv_paths, self.temp_dir)


def _next_file(indices, dest_dir):
    dest_path = Path(dest_dir)

    output_path = dest_path / f'session_0.csv'
    for session_id, next_index in enumerate(indices):
        output_handle = output_path.open('wt')
        yield output_handle, next_index

        output_handle.close()
        output_path = dest_path / f'session_{session_id+1}.csv'


def _cleanup_tmp(split_paths, temp_dir):
    for f in split_paths:
        logger.debug("Deleting %s", str(f))
        f.unlink(missing_ok=True)
    logger.debug("Deleting %s", str(temp_dir))
    temp_dir.rmdir()
