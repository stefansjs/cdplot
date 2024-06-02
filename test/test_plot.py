from argparse import Namespace
from unittest import mock

from cdplot import plot


def test_configure_axes():
    """ render_plot mutates the config before plotting """
    csv_data = Namespace(columns=['a', 'b', 'c'])
    config = {}

    plot.configure_axes(csv_data, config)

    assert config == dict(x='a', y=['b', 'c'], y2=None)

def test_plot_data_config_changes():
    csv_data = Namespace(columns=['a', 'b', 'c'])
    config = dict(type='line', layout=dict(hovermode='x'), traces=dict(hovertemplate='{}'))

    with mock.patch('plotly.express') as px:
        plot.render_plot(csv_data, config)

    assert 'type' in config
    assert 'layout' in config
    assert 'traces' in config

    px.line.assert_called()

    call_config = px.line.mock_calls[0].kwargs
    assert 'traces' not in call_config
    assert 'layout' not in call_config
    assert 'type' not in call_config

    handler = px.line.return_value
    handler.update_traces.assert_called_with(**config['traces'])
    handler.update_layout.assert_called_once_with(**config['layout'])
