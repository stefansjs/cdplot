from unittest import mock

from cdplot.__main__ import main


def test_parse_plot_args():
    args = ['a=b', 'c=2']

    with mock.patch('cdplot.__main__.plot_data') as mock_plot:
        main(args)

    config_dict = mock_plot.call_args[0][0]
    assert config_dict['plot'] == {'a': 'b', 'c': '2'}
