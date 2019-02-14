#!/usr/bin/env python3
def slice_range(start, end, n_each):
    """Generates tuples of each two bounds yielding a contiguous division of
    a total range of ascending integers from 'start' to 'end' into a set of
    closed intervals of 'n_each' ascending integers.

    If the total range cannot be divided into intervals of 'n_each'
    numbers, the residual interval is output last.
    
    'start', 'end', 'n_each': Integers

    Example: list(slice_range(-1, 7, 4)) evaluates as: [(-1, 2), (3, 6), (7, 7)]
    """
    assert end >= start and n_each > 0, "These values do not fit together!"
    i = start
    for i in range(start+n_each, end+1, n_each):
        yield i-n_each, i-1
    yield i, end
