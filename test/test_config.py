#!/usr/bin/env python

""" Unit tests for cdplot.config """
from pathlib import Path

from cdplot.config import determine_columns, normalize_config, merge_configs


def test_merge_configs():
    # empty + empty = empty
    out = merge_configs({}, {})
    assert out == {}

    # merging in an empty dict should yield the original dict as a copy
    config1 = dict(a=1, b='c', d=['a', 'b', 'c'])
    config2 = {}
    out = merge_configs(config1, config2)
    assert out is not config1
    assert out == config1

    # same thing but other way around should yield the same result
    out = merge_configs(config2, config1)
    assert out == config1
    assert out is not config1

    # handle deeper structures. Merge lists together
    config1 = dict(l=['a'])
    config2 = dict(l=['b'])
    out = merge_configs(config1, config2)
    assert out == dict(l=['a', 'b'])
    assert config1 != out
    assert config2 != out

    # merge dictionaries together
    config1 = dict(d={'a': 1})
    config2 = dict(d={'b': 2})
    out = merge_configs(config1, config2)
    assert out == dict(d={'a': 1, 'b': 2})
    assert config1 != out
    assert config2 != out

    # test dictionary recursion
    config1 = dict(d=dict(a=['b'], c=1, d={}))
    config2 = dict(d=dict(a=[1], d={'a': 2}), l=[])
    out = merge_configs(config1, config2)
    assert out == dict(l=[], d=dict(a=['b', 1], c=1, d={'a': 2}))


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
    assert output == ['a', 'c', 'a2']  # Order is not important

def test_determine_columns_exclude_patterns():
    input = ['a', 'b', 'c', 'a2', 'b2']

    # Let's test a basic include pattern
    config = dict(exclude_pattern=['*'])
    output = determine_columns(input, config)
    assert output == []

    # Test a more stringent criterion
    config = dict(exclude_pattern=['a*'])
    output = determine_columns(input, config)
    assert output == ['b', 'c', 'b2']  # Order is not preserved

    # test multiple criteria
    config = dict(exclude_pattern=['a*', 'c'])
    output = determine_columns(input, config)
    assert output == ['b', 'b2']  # Order is not preserved


def test_determine_columns_include_and_exclude():
    input = ['a', 'b', 'c', 'a2', 'b2']

    # test an include and exclude. Include should take precedence
    config = dict(include=['a'], exclude=['b'])
    output = determine_columns(input, config)
    assert output == ['a']

    # test identical inputs and outputs
    config = dict(include=['a'], exclude=['a'])
    output = determine_columns(input, config)
    assert output == []

    # test intersecting includes and excludes. Excludes run second
    config = dict(include=['a', 'b'], exclude=['b'])
    output = determine_columns(input, config)
    assert output == ['a']

    # test include pattern with exclude
    config = dict(include_pattern=['a*'], exclude='a')
    output = determine_columns(input, config)
    assert output == ['a2']

    # vice versa
    config = dict(include=['a', 'b', 'b2'], exclude_pattern=['b*'])
    output = determine_columns(input, config)
    assert output == ['a']

    # everything
    config = dict(include_pattern=['a*'], include=['b', 'c'], exclude_pattern=['b*'], exclude=['c'])
    output = determine_columns(input, config)
    assert output == ['a', 'a2']


def test_determine_columns_require():
    input = ['a', 'b', 'c', 'a2', 'b2']

    # just require should leave the list untouched
    config = dict(require=['a'])
    output = determine_columns(input, config)
    assert output == input

    # test an extra thing put in require
    config = dict(require=['d'])
    output = determine_columns(input, config)
    assert output == input

    # input + require = union of the two criteria
    config = dict(include=['a'], require=['b'])
    output = determine_columns(input, config)
    assert output == ['a', 'b']

    # requires override excludes
    config = dict(exclude_pattern=['a*'], require=['a'])
    output = determine_columns(input, config)
    assert output == ['a', 'b', 'c', 'b2']


def test_normalize_config_xaxis():
    minimum_config = dict(data=dict(csv_path="", require=[]))

    # test setting only the x-axis. I should get everything back without filters
    config = dict(minimum_config, plot=dict(x='a'))
    normalize_config(config)
    assert config == dict(data=dict(csv_path=[Path('.')], require=['a']), plot=dict(x='a'))

    # test that the x-axis gets added, even if it's filtered out
    config = dict(data=dict(csv_path="", require=[], exclude=['a']), plot=dict(x='a'))
    normalize_config(config)
    assert config == dict(data=dict(csv_path=[Path('.')], exclude=['a'], require=['a']), plot=dict(x='a'))
