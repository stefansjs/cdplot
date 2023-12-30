"""
Creates a bunch of operations to perform on columns of csv data
"""
import logging
import uuid
from functools import partial

import numpy as np

try:
    import scipy
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


logger = logging.getLogger(__name__)


def create_data_operators(config, columns):
    """ Create data operators needs to know what columns are available, so it is called after loading data """
    # If someone's already populated _operations, just use those
    if config['data'].get('_operations'):
        return list(map(Operation, config['data']['_operations']))

    # if nothing is specified, return an empty list
    if not config['data'].get('filters'):
        return []

    # build all operations and return them as an iterable of callables
    factory = OperatorFactory()
    factory.add_operations_to_config(config, columns)
    return factory.build_operations()


def process_data(dataframe, operations):
    for operation in operations:
        logger.debug("Performing %s", operation)
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
            delta_x = self.make_delta_x(config, columns)
            product = self.add_intermediate(config, source, 'product', dict(column=delta_x))
            self.add_lfilter(product, destination, coefficients=dict(numerator=[1], denominator=[1, -1]))

        elif filter_type == 'differential':
            delta_x = self.make_delta_x(config, columns)
            product = self.add_intermediate(config, source, 'product', dict(column=delta_x))
            self.add_lfilter(product, destination, coefficients=dict(numerator=[1], denominator=[1, 1]))

        elif filter_type == 'accumulator':
            self.add_lfilter(source, destination, coefficients=dict(numerator=[1], denominator=[1, -1]))

        elif filter_type in ('lti', 'lfilter', 'linear_filter'):
            self.add_lfilter(source, destination, op_config['coefficients'], op_config.get('initial_conditions'))

        elif filter_type == 'average':
            self.add_convolution(source, destination, op_config['coefficients'])

        elif filter_type == 'product':
            parameters = dict(column=op_config.get('column'), constant=op_config.get('constant'))
            self.add_product(source, destination, parameters)

        elif filter_type == 'quotient':
            parameters = dict(column=op_config.get('column'), constant=op_config.get('constant'))
            self.add_quotient(source, destination, parameters)

        elif filter_type == 'sum':
            parameters = dict(column=op_config.get('column'), constant=op_config.get('constant'))
            self.add_sum(source, destination, parameters)

        elif filter_type == 'difference':
            parameters = dict(column=op_config.get('column'), constant=op_config.get('constant'),
                              align=op_config.get('align'), dtype=op_config.get('dtype'))
            self.add_difference(source, destination, parameters)


    def add_operation(self, source, destination, op_type, op_parameters):
        self.operations.append(self.build_op(source, destination, op_type, op_parameters))

    def add_intermediate(self, config, source, op_type, op_params, name=None):
        if name is not None and name in self._intermediates:
            return  # short-circuit if it's already been added. This had better work

        if name is None:
            # If the destination doesn't have a name, create a unique name for it
            name = f'plot_torque_pro-{len(self._intermediates)}-{uuid.uuid4()}'

        op_config = self.build_op(source, name, op_type, op_params)
        self.operations.append(op_config)
        self._intermediates[name] = op_config
        config['data']['exclude'].append(name)

        return name

    @staticmethod
    def build_op(source, destination, op_type, op_params):
        return dict(source=source, destination=destination, type=op_type, **op_params)


    def add_lfilter(self, source, destination, coefficients, initial_conditions=None):
        """ Add a linear filter """
        config = dict(coefficients=coefficients, initial_conditions=initial_conditions)
        self.add_operation(source, destination, 'lfilter', config)

    def add_convolution(self, source, destination, window, offset=None):
        self.add_operation(source, destination, 'convolution', dict(window=window, offset=offset))

    def add_product(self, source, destination, config):
        """ Add a multiplication operation """
        self.add_operation(source, destination, 'product', config)

    def add_quotient(self, source, destination, config):
        self.add_operation(source, destination, 'quotient', config)

    def add_sum(self, source, destination, config):
        """ Add a multiplication operation """
        self.add_operation(source, destination, 'sum', config)

    def add_difference(self, source, destination, config):
        """ Add a multiplication operation """
        self.add_operation(source, destination, 'difference', config)


    def make_delta_x(self, config, columns):
        x_axis = config['plot'].get('x', columns[0])
        column = 'delta_x'

        if column in self._intermediates:
            return column

        one_hour = np.timedelta64(1, 'h')
        timedelta = self.add_intermediate(config, x_axis, 'difference', op_params=(dict(align='right')))
        self.add_intermediate(config, timedelta, 'quotient', op_params=dict(constant=one_hour), name=column)

        return column


class Operation:
    def __init__(self, op_config):
        self.source = op_config['source']
        self.dest = op_config['destination']
        self.operation = op_config['type']
        self._func = self.build_operation(op_config)

    def __call__(self, csv_dataframe):
        csv_dataframe[self.dest] = self._func(csv_dataframe)

    def __str__(self):
        return f'{self.operation}("{self.source}" => "{self.dest}"): {self._func}'


    def _default(self, csv_dataframe, bound_operator):
        return bound_operator(csv_dataframe[self.source])

    def _do_filter(self, csv_dataframe, lfilter):
        return lfilter(csv_dataframe[self.source])

    def _do_difference(self, csv_dataframe, constant=None, column=None, align=None, dtype=None):
        source = csv_dataframe[self.source].to_numpy()

        if constant is not None:
            return source - constant

        elif column is not None:
            return source - csv_dataframe[column].array

        # else, produce a difference signal by subtracting adjacent values from one another
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
        if column:
            return csv_dataframe[self.source] * csv_dataframe[column]
        else:
            return csv_dataframe[self.source] * constant

    def _do_divide(self, csv_dataframe, constant=None, column=None):
        if column:
            return csv_dataframe[self.source] / csv_dataframe[column]
        else:
            return csv_dataframe[self.source] / constant


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

        if op_type == 'quotient':
            if op_config.get('column'):
                return bind(self._do_divide, column=op_config['column'])
            else:
                return bind(self._do_divide, constant=op_config['constant'])

        if op_type == 'difference':
            if op_config.get('column'):
                return bind(self._do_difference, column=op_config['column'])
            elif op_config.get('constant') is not None:
                return bind(self._do_difference, constant=op_config['constant'])
            else:
                return bind(self._do_difference, align=op_config.get('align'), dtype=op_config.get('dtype'))

        if op_type == 'convolution':
            return bind(self._do_filter, bind(scipy.signal.convolve, in2=op_config['window']))


def bind(method, *op_args, **op_kwargs):
    return partial(method, *op_args, **op_kwargs)
