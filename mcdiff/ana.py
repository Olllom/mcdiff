

from __future__ import print_function

import charmm


def do_analysis(args):
    """
    Entry point for the analysis.
    """
    pass


class Result(object):
    def __init__(self, sim_id, lag_time, file):
        self.sim_id = sim_id
        self.lag_time = lag_time
        self.file = file


class SystemProfiles(object):
    """
    A class to store the resulting profiles for a single system.
    """
    def __init__(self):
        pass

    @staticmethod
    def read_from_config(self, config):
        pass

    pass


def extrapolate_to_infinity():
    pass


def permeability():
    pass