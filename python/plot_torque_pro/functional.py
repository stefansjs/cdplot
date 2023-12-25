"""
Just a series of helper functions for doing some functional-programming related things
"""
from itertools import chain


# I just find that I'm constantly doing list( <some other functional tasks> ) quite often


def lfilter(*args):
    """ list of filter of args """
    return list(filter(*args))


def lchain(*args):
    """ list of chain of args '"""
    return list(chain(*args))

