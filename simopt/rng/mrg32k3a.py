"""
Summary
-------
Provide a subclass of random.Random using mrg32k3a as the generator
with stream/substream/subsubstream support.

Listing
-------
MRG323k3a
advance_stream
advance_substream
advance_subsubstream
reset_stream
reset_substream
reset_subsubstream
start_fixed_s_ss_sss
"""

# code largely adopted from PyMOSO repository (https://github.com/pymoso/PyMOSO)

import random
from math import log
import functools
from matmodops import mat33_mat31_mult, mat33_mat33_mult, mat31_mod, mat33_mod, mat33_mat33_mod, mat33_power_mod

## constants used in mrg32k3a and in substream generation
## all from:
 # P. L'Ecuyer, ``Good Parameter Sets for Combined Multiple Recursive Random Number Generators'',
 # Operations Research, 47, 1 (1999), 159--164.
 #
 # P. L'Ecuyer, R. Simard, E. J. Chen, and W. D. Kelton,
 # ``An Objected-Oriented Random-Number Package with Many Long Streams and Substreams'',
 # Operations Research, 50, 6 (2002), 1073--1075

mrgnorm = 2.328306549295727688e-10
mrgm1 = 4294967087
mrgm2 = 4294944443
mrga12 = 1403580
mrga13n = 810728
mrga21 = 527612
mrga23n = 1370589

A1p0 =  [[0, 1, 0],
    [0, 0, 1],
    [-mrga13n, mrga12, 0]
]

A2p0 =  [[0, 1, 0],
    [0, 0, 1],
    [-mrga23n, 0, mrga21]
]

# A1p47 = matrix_power_mod(A1p0, 2**47, mrgm1)
A1p47 = [[1362557480, 3230022138, 4278720212],
    [3427386258, 3848976950, 3230022138],
    [2109817045, 2441486578, 3848976950]
]

# A2p47 = matrix_power_mod(A2p0, 2**47, mrgm2)
A2p47 = [[2920112852, 1965329198, 1177141043],
    [2135250851, 2920112852, 969184056],
    [296035385, 2135250851, 4267827987]
]

# A1p94 = matrix_power_mod(A1p0, 2**94, mrgm1)
A1p94 = [[2873769531, 2081104178, 596284397],
    [4153800443, 1261269623, 2081104178],
    [3967600061, 1830023157, 1261269623]
]

# A2p94 = matrix_power_mod(A2p0, 2**94, mrgm2)
A2p94 = [[1347291439, 2050427676, 736113023],
    [4102191254, 1347291439, 878627148],
    [1293500383, 4102191254, 745646810]
]

# A1p141 = matrix_power_mod(A1p0, 2**141, mrgm1)
A1p141 = [[3230096243, 2131723358, 3262178024],
    [2882890127, 4088518247, 2131723358],
    [3991553306, 1282224087, 4088518247]
]

# A2p141 = matrix_power_mod(A2p0, 2**141, mrgm2)
A2p141 = [[2196438580, 805386227, 4266375092],
    [4124675351, 2196438580, 2527961345],
    [94452540, 4124675351, 2825656399]
]

# this is adapted to pure Python from the P. L'Ecuyer code referenced above
def mrg32k3a(state):
    """
    Generate a random number between 0 and 1 from a given state.

    Arguments
    ---------
    state : tuple of int of length 6
        current state of the generator

    Returns
    -------
    new_state : tuple of int of length 6
        next state of the generator
    u : float
        pseudo uniform random variate
    """
    # Component 1
    p1 = mrga12*state[1] - mrga13n*state[0]
    k1 = int(p1/mrgm1)
    p1 -= k1*mrgm1
    if p1 < 0.0:
        p1 += mrgm1
    # Component 2
    p2 = mrga21*state[5] - mrga23n*state[3]
    k2 = int(p2/mrgm2)
    p2 -= k2*mrgm2
    if p2 < 0.0:
        p2 += mrgm2
    # Combination
    if p1 <= p2:
        u = (p1 - p2 + mrgm1)*mrgnorm
    else:
        u = (p1 - p2)*mrgnorm
    new_state = (state[1], state[2], int(p1), state[4], state[5], int(p2))
    return new_state, u

class MRG32k3a(random.Random):
    """
    Implements mrg32k3a as the generator for a random.Random object.

    Attributes
    ----------
    _current_state : tuple of int of length 6
        current state of mrg32k3a generator
    ref_seed : tuple of int of length 6
        seed from which to start the generator
        streams/substreams/subsubstreams are referenced w.r.t. ref_seed 
    s_ss_sss_index : list of int of length 3
        triplet of the indices of the current stream-substream-subsubstream
    stream_start : list of int of length 6
        state corresponding to the start of the current stream
    substream_start: list of int of length 6
        state corresponding to the start of the current substream
    subsubstream_start: list of int of length 6
        state corresponding to the start of the current subsubstream

    Arguments
    ---------
    ref_seed : tuple of int of length 6 (optional)
        seed from which to start the generator

    See also
    --------
    random.Random
    """
    def __init__(self, ref_seed = (12345, 12345, 12345, 12345, 12345, 12345)):
        assert(len(ref_seed) == 6)
        self.version = 2
        self.generate = mrg32k3a
        self.ref_seed = ref_seed
        start_fixed_s_ss_sss(self, [0, 0, 0])
        super().__init__(ref_seed)

    def seed(self, new_state):
        """
        Set the state (or seed) of the generator and update the generator state.

        Arguments
        ---------
        new_state : tuple of int of length 6
            new state to which to advance the generator
        """
        assert(len(new_state) == 6)
        self._current_state = new_state
        super().seed(new_state)

    def random(self):
        """
        Generate a standard uniform variate and advance the generator
        state.

        Returns
        -------
        u : float
            pseudo uniform random variate
        """
        state = self._current_state
        new_state, u = self.generate(state)
        self.seed(new_state)
        return u

    def get_current_state(self):
        """
        Return the current state of the generator.

        Returns
        -------
        _current_state : tuple of int of length 6
            current state of the generator
        """
        return self._current_state

    def getstate(self):
        """
        Return the state of the generator.

        Returns
        -------
        _current_state : tuple of int of length 6
            current state of the generator
        random.Random.getstate() : tuple of int
            Random.getstate output

        See also
        --------
        random.Random
        """
        return self.get_current_state(), super().getstate()

    def setstate(self, state):
        """
        Set the internal state of the generator.

        Arguments
        ---------
        state : tuple
            state[0] is new state for the generator
            state[1] is random.Random.getstate()

        See also
        --------
        random.Random
        """
        self.seed(state[0])
        super().setstate(state[1])

def advance_stream(rng):
    """
    Advance the state of the generator to the start of the next stream.
    Streams are of length 2**141.

    Arguments
    ---------
    rng : MRG32k3a object
        mrg32k3a generator
    """
    state = rng.stream_start
    # split the state into 2 components of length 3
    st1 = state[0:3]
    st2 = state[3:6]
    # efficiently advance state -> A*s % m for both state parts
    nst1m = mat33_mat31_mult(A1p141, st1)
    nst2m = mat33_mat31_mult(A2p141, st2)
    nst1 = mat31_mod(nst1m, mrgm1)
    nst2 = mat31_mod(nst2m, mrgm2)
    nstate = tuple(nst1 + nst2)
    rng.seed(nstate)
    # increment the stream index
    rng.s_ss_sss_index[0] += 1
    # update state referencing
    rng.stream_start = nstate
    rng.substream_start = nstate
    rng.subsubstream_start = nstate

def advance_substream(rng):
    """
    Advance the state of the generator to the start of the next substream.
    Substreams are of length 2**94.

    Arguments
    ---------
    rng : MRG32k3a object
        mrg32k3a generator
    """
    state = rng.substream_start
    # split the state into 2 components of length 3
    st1 = state[0:3]
    st2 = state[3:6]
    # efficiently advance state -> A*s % m for both state parts
    nst1m = mat33_mat31_mult(A1p94, st1)
    nst2m = mat33_mat31_mult(A2p94, st2)
    nst1 = mat31_mod(nst1m, mrgm1)
    nst2 = mat31_mod(nst2m, mrgm2)
    nstate = tuple(nst1 + nst2)
    rng.seed(nstate)
    # increment the substream index
    rng.s_ss_sss_index[1] += 1
    # update state referencing
    rng.substream_start = nstate
    rng.subsubstream_start = nstate

def advance_subsubstream(rng):
    """
    Advance the state of the generator to the start of the next subsubstream.
    Subsubstreams are of length 2**47.

    Arguments
    ---------
    rng : MRG32k3a object
        mrg32k3a generator
    """
    state = rng.subsubstream_start
    # split the state into 2 components of length 3
    st1 = state[0:3]
    st2 = state[3:6]
    # efficiently advance state -> A*s % m for both state parts
    nst1m = mat33_mat31_mult(A1p47, st1)
    nst2m = mat33_mat31_mult(A2p47, st2)
    nst1 = mat31_mod(nst1m, mrgm1)
    nst2 = mat31_mod(nst2m, mrgm2)
    nstate = tuple(nst1 + nst2)
    rng.seed(nstate)
    # increment the subsubstream index
    rng.s_ss_sss_index[2] += 1
    # update state referencing
    rng.subsubstream_start = nstate

def reset_stream(rng):
    """
    Reset the state of the generator to the start of the current stream.

    Arguments
    ---------
    rng : MRG32k3a object
        mrg32k3a generator
    """
    nstate = rng.stream_start
    rng.seed(nstate)
    # update state referencing
    rng.substream_start = nstate
    rng.subsubstream_start = nstate
    # reset index for substream and subsubstream
    rng.s_ss_sss_index[1] = 0
    rng.s_ss_sss_index[2] = 0

def reset_substream(rng):
    """
    Reset the state of the generator to the start of the current substream.

    Parameters
    ----------
    rng : MRG32k3a object
        mrg32k3a generator
    """
    nstate = rng.substream_start
    rng.seed(nstate)
    # update state referencing
    rng.subsubstream_start = nstate
    # reset index for substream and subsubstream
    rng.s_ss_sss_index[2] = 0

def reset_subsubstream(rng):
    """
    Reset the state of the generator to the start of the current subsubstream.

    Parameters
    ----------
    rng : MRG32k3a object
        mrg32k3a generator
    """
    nstate = rng.subsubstream_start
    rng.seed(nstate)

def start_fixed_s_ss_sss(rng, s_ss_sss_triplet):
    """
    Set the rng to the start of a specified (stream, substream, subsubstream) triplet.

    Arguments
    ---------
    rng : MRG32k3a object
        mrg32k3a generator
    s_ss_sss_triplet : list of int of length 3
        triplet of the indices of the current stream-substream-subsubstream
    """
    state = rng.ref_seed
    # split the reference seed into 2 components of length 3
    st1 = state[0:3]
    st2 = state[3:6]
    # advance to start of specified stream
    for _ in range(s_ss_sss_triplet[0]):
        # efficiently advance state -> A*s % m for both state parts
        nst1m = mat33_mat31_mult(A1p141, st1)
        nst2m = mat33_mat31_mult(A2p141, st2)
        st1 = mat31_mod(nst1m, mrgm1)
        st2 = mat31_mod(nst2m, mrgm2)
    rng.stream_start = tuple(st1 + st2)
    # advance to start of specified substream
    for _ in range(s_ss_sss_triplet[1]):
        # efficiently advance state -> A*s % m for both state parts
        nst1m = mat33_mat31_mult(A1p94, st1)
        nst2m = mat33_mat31_mult(A2p94, st2)
        st1 = mat31_mod(nst1m, mrgm1)
        st2 = mat31_mod(nst2m, mrgm2)
    rng.substream_start = tuple(st1 + st2)
    # advance to start of specified subsubstream
    for _ in range(s_ss_sss_triplet[2]):
        # efficiently advance state -> A*s % m for both state parts
        nst1m = mat33_mat31_mult(A1p47, st1)
        nst2m = mat33_mat31_mult(A2p47, st2)
        st1 = mat31_mod(nst1m, mrgm1)
        st2 = mat31_mod(nst2m, mrgm2)
    rng.subsubstream_start = tuple(st1 + st2)
    nstate = tuple(st1 + st2)
    rng.seed(nstate)
    # update index referencing
    rng.s_ss_sss_index = s_ss_sss_triplet