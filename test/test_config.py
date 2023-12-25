#!/usr/bin/env python

""" Unit tests for plot_torque_pro.config """
from pathlib import Path

from plot_torque_pro.config import determine_columns, normalize_config


def test_determine_columns_nothing():
    input = ['a', 'b', 'c']

    # No parameters means I should always get back everything
    config = dict(data={}, plot={})
    output = determine_columns(input, config)
    assert input == output


def test_determin_columns_includes():
    input = ['a', 'b', 'c']

    # the "include" parameter should filter out everything else
    config = dict(plot={}, data=dict(include=['c']))
    output = determine_columns(input, config)
    assert output == ['c']

    # and an absent column should yield an empty list
    config = dict(plot={}, data=dict(include=['d']))
    output = determine_columns(input, config)
    assert output == []

    # and of course multiple includes should work too
    config = dict(plot={}, data=dict(include=['a', 'b']))
    output = determine_columns(input, config)
    assert output == ['a', 'b']


def test_determine_columns_include_patterns():
    input = ['a', 'b', 'c', 'a2', 'b2']

    # Let's test a basic include pattern
    config = dict(plot={}, data=dict(include_pattern=['*']))
    output = determine_columns(input, config)
    assert input == output

    # Test a more stringent criterion
    config = dict(plot={}, data=dict(include_pattern=['a*']))
    output = determine_columns(input, config)
    assert output == ['a', 'a2']

    # test multiple criteria
    config = dict(plot={}, data=dict(include_pattern=['a*', 'c']))
    output = determine_columns(input, config)
    assert set(output) == {'a', 'c', 'a2'}  # Order is not important

def test_determine_columns_exclude_patterns():
    input = ['a', 'b', 'c', 'a2', 'b2']

    # Let's test a basic include pattern
    config = dict(plot={}, data=dict(exclude_pattern=['*']))
    output = determine_columns(input, config)
    assert output == []

    # Test a more stringent criterion
    config = dict(plot={}, data=dict(exclude_pattern=['a*']))
    output = determine_columns(input, config)
    assert set(output) == {'b', 'c', 'b2'}  # Order is not preserved

    # test multiple criteria
    config = dict(plot={}, data=dict(exclude_pattern=['a*', 'c']))
    output = determine_columns(input, config)
    assert set(output) == {'b', 'b2'}  # Order is not preserved


def test_determine_columns_include_and_exclude():
    input = ['a', 'b', 'c', 'a2', 'b2']

    # test an include and exclude. Include should take precedence
    config = dict(plot={}, data=dict(include=['a'], exclude=['b']))
    output = determine_columns(input, config)
    assert output == ['a']

    # test identical inputs and outputs
    config = dict(plot={}, data=dict(include=['a'], exclude=['a']))
    output = determine_columns(input, config)
    assert output == []

    # test intersecting includes and excludes. Excludes run second
    config = dict(plot={}, data=dict(include=['a', 'b'], exclude=['b']))
    output = determine_columns(input, config)
    assert output == ['a']

    # test include pattern with exclude
    config = dict(plot={}, data=dict(include_pattern=['a*'], exclude='a'))
    output = determine_columns(input, config)
    assert output == ['a2']

    # vice versa
    config = dict(plot={}, data=dict(include=['a', 'b', 'b2'], exclude_pattern=['b*']))
    output = determine_columns(input, config)
    assert output == ['a']

    # everything
    config = dict(plot={}, data=dict(include_pattern=['a*'], include=['b', 'c'], exclude_pattern=['b*'], exclude=['c']))
    output = determine_columns(input, config)
    assert output == ['a', 'a2']


def test_determine_columns_require():
    input = ['a', 'b', 'c', 'a2', 'b2']

    # just require should leave the list untouched
    config = dict(plot={}, data=dict(require=['a']))
    output = determine_columns(input, config)
    assert output == input

    # test an extra thing put in require
    config = dict(plot={}, data=dict(require=['d']))
    output = determine_columns(input, config)
    assert output == input

    # input + require = union of the two criteria
    config = dict(plot={}, data=dict(include=['a'], require=['b']))
    output = determine_columns(input, config)
    assert output == ['a', 'b']

    # requires override excludes
    config = dict(plot={}, data=dict(exclude_pattern=['a*'], require=['a']))
    output = determine_columns(input, config)
    assert set(output) == {'a', 'b', 'c', 'b2'}


def test_normalize_config_xaxis():
    minimum_config = dict(data=dict(csv_path="", require=[]))

    # test setting only the x-axis. I should get everything back without filters
    config = dict(minimum_config, plot=dict(x='a'))
    normalize_config(config)
    assert config == dict(data=dict(csv_path=Path('.'), require=['a']), plot=dict(x='a'))

    # test that the x-axis gets added, even if it's filtered out
    config = dict(data=dict(csv_path="", require=[], exclude=['a']), plot=dict(x='a'))
    normalize_config(config)
    assert config == dict(data=dict(csv_path=Path('.'), exclude=['a'], require=['a']), plot=dict(x='a'))
