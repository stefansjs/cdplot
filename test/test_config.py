#!/usr/bin/env python

""" Unit tests for plot_torque_pro.config """
from plot_torque_pro.config import determine_columns


def test_determine_columns_nothing():
    input = ['a', 'b', 'c']

    # No parameters means I should always get back everything
    output = determine_columns(input, {})
    assert input == output


def test_determin_columns_includes():
    input = ['a', 'b', 'c']

    # the "include" parameter should filter out everything else
    config = dict(include=['c'])
    output = determine_columns(input, config)
    assert output == ['c']

    # and an absent column should yield an empty list
    config = dict(include=['d'])
    output = determine_columns(input, config)
    assert output == []

    # and of course multiple includes should work too
    config = dict(include=['a', 'b'])
    output = determine_columns(input, config)
    assert output == ['a', 'b']


def test_determine_columns_include_patterns():
    input = ['a', 'b', 'c', 'a2', 'b2']

    # Let's test a basic include pattern
    config = dict(include_pattern=['*'])
    output = determine_columns(input, config)
    assert input == output

    # Test a more stringent criterion
    config = dict(include_pattern=['a*'])
    output = determine_columns(input, config)
    assert output == ['a', 'a2']

    # test multiple criteria
    config = dict(include_pattern=['a*', 'c'])
    output = determine_columns(input, config)
    assert set(output) == {'a', 'c', 'a2'}  # Order is not important


