"""
Reads and plots data from csv
"""
import logging
import re
import tempfile
from collections import defaultdict
from pathlib import Path

import pandas
from pandas._libs.lib import no_default

logger = logging.getLogger(__name__)


def load_from_csv(config):
    csv_path = config['csv_path']
    read_csv = config['read_csv']

    if not csv_path:
        raise ValueError("Nothing to plot")

    # Because read_csv allows you to pass a defaultdict(), and that can't be represented in toml,
    # we add default_type and do this custom logic
    if config.get('default_type'):
        dtypes = defaultdict(lambda: config['default_type'])
        dtypes.update(read_csv.get('dtype', {}))
    else:
        dtypes = read_csv.get('dtype')

    read_args = dict(read_csv, dtype=dtypes)

    # Split the data into multiple CSVs if necessary
    with preprocess_data(*csv_path) as sessions:
        if config.get('session') is not None:
            csv_dataframe = pandas.read_csv(sessions[config['session']], **read_args)
        elif len(sessions) == 1:
            csv_dataframe = pandas.read_csv(sessions[0], **read_args)
        else:
            all_dataframes = [pandas.read_csv(f, **read_args) for f in sessions]
            csv_dataframe = pandas.concat(all_dataframes)

    if config.get('dropna', False):
        csv_dataframe.dropna(inplace=True, thresh=config.get('dropna_threshold', no_default))
    elif config.get('fillna') is not None:
        csv_dataframe.fillna(config['fillna'], inplace=True)

    return csv_dataframe


def preprocess_data(*csv_paths):
    """
    Splits each csv files into one or more "session" csv files and returns a flat list of all session files

    CSV files are allows to have multiple header rows. Each time we see a header, we might have different columns.
    Split each into "session" csv files every time we see a new header row.
    """
    session_paths = []
    temp_dir = Path(tempfile.mkdtemp(prefix='cdplot_'))

    for csv_path in csv_paths:
        session_paths.extend(preprocess_csv(csv_path, temp_dir, len(session_paths)))

    return TemporaryCSV(session_paths, temp_dir)


def preprocess_csv(csv_path, temp_dir, starting_session=0):
    """ Looks for likely header rows, and calls split_csv to output multiple "session" csv files """
    header_indices = []
    with csv_path.open() as fh:
        for index, line in enumerate(fh):
            has_numeric = re.search(r'(,\s?-?\d+([\.,]\d*)?([eE]\d+[\.,]?\d*)?,)+', line)
            if has_numeric is None:
                logger.debug("session %d = %s", len(header_indices), line.strip())
                header_indices.append(index)

    # split the file into multiple files, and cleanup data
    split_indices = header_indices + [index + 1]
    return split_csv(csv_path, split_indices, temp_dir, starting_session)


def split_csv(csv_path, split_indices, temp_dir, starting_session=0):
    """ Writes multiple csv files from one csv file, splitting at the given rows """
    split_indices = split_indices[1:] if split_indices[0] == 0 else split_indices

    with csv_path.open() as fh:
        output_iter = iter(CSVSplitter(split_indices, temp_dir, starting_session))
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
            _cleanup_tmp(split_paths + [Path(output_handle.name)], temp_dir)
            raise

    return split_paths


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


class CSVSplitter:
    def __init__(self, indices, dest_dir, start_index=0):
        self.indices = indices
        self.dest_path = Path(dest_dir)
        self.start_index = start_index

    def __iter__(self):
        output_path = self.dest_path / f'session_{self.start_index}.csv'
        for session_index, next_index in enumerate(self.indices):
            output_handle = output_path.open('wt')
            yield output_handle, next_index

            output_handle.close()
            output_path = self.dest_path / f'session_{self.start_index + session_index + 1}.csv'


def _cleanup_tmp(split_paths, temp_dir):
    for f in split_paths:
        logger.debug("Deleting %s", str(f))
        f.unlink(missing_ok=True)
    logger.debug("Deleting %s", str(temp_dir))
    temp_dir.rmdir()
