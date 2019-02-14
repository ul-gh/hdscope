# -*- coding: utf-8 -*-
"""
Basic signal processing
"""
import sys
import numpy as np
import pandas as pd
import scipy.signal

def downsample_average(x, N):
    """Downsample using simple average as anti-aliasing filter.
    
    This is not only fastest but offers best possible random noise
    reduction, yielding enhanced resolution when sufficient white noise is
    present. Extra resolution bits are log(N)/log(4).

    Disadvantage is poor frequency stopband attenuation.
    Use this as the first step of any further processing.
    """
    assert x.size % N == 0, "Input vector must be divisible by N"
    return np.mean(x.reshape(-1, N), axis=1)

def moving_average1(x, N):
    # Fast. Processing 100 megasample float values needs approx. 4 GiB RAM.
    # See: https://stackoverflow.com/a/27681394/675674
    cumsum = np.cumsum(np.insert(x, 0, 0)) 
    return (cumsum[N:] - cumsum[:-N]) / float(N)

def moving_average2(x, N):
    # Uses convolution. Approx. 10x slower than np.cumsums but uses less
    # memory: approx. 2.5 GiB for 100 megasamples.
    return np.convolve(x, np.ones((N,))/N, mode="valid")
    
def moving_average3(x, N):
    # Uses convolution via FFT and IFFT. Similar speed than np.convolve but
    # much more memory usage, approx. 8.5 GiB for 100 megasamples.
    return scipy.signal.fftconvolve(x, np.ones((N,))/N, mode="valid")
    
def moving_average4(x, N):
    # Using pandas, approx. 4x slower than np.cumsum. Approx. 8 GiB for 100
    # megasamples.
    return pd.Series(x).rolling(window=N).mean().iloc[N-1:].values
