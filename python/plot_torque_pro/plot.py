"""
Reads and plots data from csv
"""
import logging

import plotly.express
from plotly.subplots import make_subplots

from .functional import lfilter

logger = logging.getLogger(__name__)


def render_plot(csv_data, plot_config):
    configure_axes(csv_data, plot_config)

    fig = plotly.express.line(csv_data, x=plot_config['x'], y=plot_config['y'])

    if plot_config['y2']:
        twin_axes = make_subplots(specs=[[dict(secondary_y=True)]])

        right_axis = plotly.express.line(csv_data, x=plot_config['x'], y=plot_config['y2'])
        right_axis.update_traces(yaxis='y2')

        twin_axes.add_traces(fig.data + right_axis.data)
        fig = twin_axes

    return fig


def configure_axes(csv_dataframe, config):
    plot_columns = list(csv_dataframe.columns)

    # Make sure we handle the x-axis
    x_axis = config.get('x')
    y_axis = config.get('y')
    y2_axis = config.get('y2')

    if x_axis is None and y_axis is None:
        x_axis = plot_columns[0]
        y_axis = plot_columns[1:]

    if y_axis is None:
        y_axis = list(plot_columns)
        y_axis.remove(x_axis)

    if y2_axis is not None:
        y_axis = lfilter(lambda c: c not in set(y2_axis), y_axis)

    config['x'] = x_axis
    config['y'] = y_axis
    config['y2'] = y2_axis
