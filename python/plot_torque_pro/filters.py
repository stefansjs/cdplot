"""
Creates a bunch of operations to perform on columns of csv data
"""
from functools import partial

import numpy as np

try:
    import scipy
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False



def create_data_operators(config, columns):
    """ Create data operators needs to know what columns are available, so it is called after loading data """
    # If someone's already populated _operations, just use those
    if config['data'].get('_operations'):
        return list(map(Operation, config['_operations']))

    # if nothing is specified, return an empty list
    if not config['data'].get('filters'):
        return []

    # build all operations and return them as an iterable of callables
    factory = OperatorFactory()
    factory.add_operations_to_config(config, columns)
    return factory.build_operations()


def process_data(dataframe, operations):
    for operation in operations:
        operation(dataframe)

    return dataframe


class OperatorFactory:
    """ Stateful class for instantiating """

    # enum constant
    X_AXIS = "< UNSPECIFIED X-AXIS >"

    def __init__(self):
        self._intermediates = {}
        self.operations = []


    def build_operations(self):
        return map(Operation, self.operations)


    def add_operations_to_config(self, config, columns):
        # Initialize config
        config['data']['_operations'] = []
        # hold a reference to that list so that we can modify it as build operations
        self.operations = config['data']['_operations']

        for filter_config in config['data'].get('filters'):
            self.add_operator(config, filter_config, columns)

    def add_operator(self, config, op_config, columns):
        """ Data operators should be created after data is loaded so that we know what the x_axis is """

        source = op_config['source']
        destination = op_config.get('destination', source)
        filter_type = op_config.get('type', 'lti')

        if filter_type == 'integral':
            self.make_delta_x(config, columns)
            self.add_lfilter(source, destination, coefficients=dict(numerator=[1, 0], denominator=[1, -1]))
            self.add_product(destination, destination, dict(column='delta_x'))

        elif filter_type == 'differential':
            self.make_delta_x(config, columns)
            self.add_lfilter(source, destination, coefficients=dict(numerator=[1, 0], denominator=[1, 1]))
            self.add_product(destination, destination, dict(column='delta_x'))

        elif filter_type == 'accumulator':
            self.add_lfilter(source, destination, coefficients=dict(numerator=[1, 0], denominator=[1, -1]))

        elif filter_type in ('lti', 'lfilter', 'linear_filter'):
            self.add_lfilter(source, destination, op_config['coefficients'], op_config.get('initial_conditions'))

        elif filter_type == 'average':
            self.add_convolution(source, destination, op_config['coefficients'])

        elif filter_type == 'product':
            parameters = dict(column=op_config.get('column'), constant=op_config.get('constant'))
            self.add_product(source, destination, parameters)


    def add_operation(self, source, destination, op_config):
        self.operations.append(dict(source=source, destination=destination, **op_config))


    def add_lfilter(self, source, destination, coefficients, initial_conditions=None):
        """ Add a linear filter """
        config = dict(type='lfilter', coefficients=coefficients, initial_conditions=initial_conditions)
        self.add_operation(source, destination, config)


    def add_convolution(self, source, destination, window, offset=None):
        self.add_operation(source, destination, dict(type='convolution', window=window, offset=offset))


    def add_product(self, source, destination, config):
        """ Add a multiplication operation """
        self.add_operation(source, destination, dict(type='product', **config))


    def make_delta_x(self, config, columns):
        x_axis = config['plot'].get('x', columns[0])

        if 'delta_x' in self._intermediates:
            return

        delta_x = {
            'source': x_axis,
            'destination': 'delta_x',
            'type': 'difference',
            'align': 'right',
            'dtype': 'float64',
        }
        self._intermediates['delta_x'] = delta_x
        self.operations.append(delta_x)

        config['data']['exclude'].append('delta_x')


class Operation:
    def __init__(self, op_config):
        self.source = op_config['source']
        self.dest = op_config['destination']
        self._func = self.build_operation(op_config)

    def __call__(self, csv_dataframe):
        csv_dataframe[self.dest] = self._func(csv_dataframe)


    def _default(self, csv_dataframe, bound_operator):
        return bound_operator(csv_dataframe[self.source])

    def _do_filter(self, csv_dataframe, lfilter):
        return lfilter(csv_dataframe[self.source])

    def _do_difference(self, csv_dataframe, align=None, dtype=None):
        source = csv_dataframe[self.source].array
        diff = source[1:] - source[:-1]

        if align == 'left':
            padded = np.zeros(source.shape, dtype=dtype or diff.dtype)
            padded[:-1] = diff
            return padded

        elif align == 'right':
            padded = np.zeros(source.shape, dtype=dtype or diff.dtype)
            padded[1:] = diff
            return padded

        return diff

    def _do_multiply(self, csv_dataframe, constant=None, column=None):
        if constant:
            return csv_dataframe[self.source] * constant
        else:
            return csv_dataframe[self.source] * csv_dataframe[column]


    def build_operation(self, op_config):
        op_type = op_config['type']
        if op_type == 'lfilter':
            coeffs = op_config['coefficients']
            dtype = coeffs.get('dtype', 'float64')
            numerator = np.array(coeffs['numerator'], dtype=dtype)
            denominator = np.array(coeffs['denominator'], dtype=dtype)

            zi = op_config.get('initial_conditions')
            return bind(self._do_filter,
                        lfilter=bind(scipy.signal.lfilter, numerator, denominator, zi=zi))

        if op_type == 'product':
            if op_config.get('column'):
                return bind(self._do_multiply, column=op_config['column'])
            else:
                return bind(self._do_multiply, constant=op_config['constant'])

        if op_type == 'difference':
            return bind(self._do_difference, align=op_config['align'], dtype=op_config.get('dtype'))

        if op_type == 'convolution':
            return bind(self._do_filter, bind(scipy.signal.convolve, in2=op_config['window']))


def bind(method, *op_args, **op_kwargs):
    return partial(method, *op_args, **op_kwargs)
