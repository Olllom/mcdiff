"""
Command line interface for 'mcdiff' and subcommands.
"""

from __future__ import print_function

import os
from argparse import ArgumentParser

from six.moves import configparser

from mc import find_parameters
from outreading import read_many_profiles
from outreading import read_many_profiles_Drad
from plot import make_plots
import charmm


def run(options):
    print("options:")
    print(options.__dict__)
    # check arguments
    assert len(options.trans_mat_files) >= 1
    print("="*20)
    find_parameters(options.trans_mat_files, options.pbc, options.model,
                options.dv, options.dw, options.dwrad, options.D0, options.dtimezero,
                options.temp, options.temp_end,
                options.nmc, options.nmc_update,
                options.seed,
                options.outfile,
                options.ncosF, options.ncosD, options.ncosDrad,
                options.move_timezero,
                options.initfile,
                options.k,
                options.lmax,
                options.reduction)


def parse_run(parser):
    parser.add_argument("trans_mat_files", nargs='+')
    parser.add_argument("-o", "--outfile", dest="outfile", default=None,
                        help="filename FILE where F and D results will be stored")
    parser.add_argument("--nopbc", dest="pbc", default=True,
                        action="store_false",
                        help="when no periodic boundary conditions should be used")
    parser.add_argument("--initf", dest="initfile", default=None,
                        help="filename FILE with initial guess for F, D, dv, dw")
    parser.add_argument("-n","--nmc", dest="nmc", default=1000,
                        type=int,
                        help="number of Monte Carlo cycles")
    parser.add_argument("-T", dest="temp", default=1.,
                        type=float,
                        help="temperature in parameter space in Monte Carlo run")
    parser.add_argument("--Tend", dest="temp_end", default=0.01,
                        type=float,
                        help="temperature in parameter space in Monte Carlo run, "
                           "attained by updating every nmc_update steps")
    parser.add_argument("--nbins", dest="nbins", default=None,
                        type=int,
                        help="number of bins (usually equals number of edges minus one)")
    #parser.add_argument("--dt", dest="dt", default=1.,   # in ps   # TODO this just the unit
    #                  type="float",
    #                  help="time step in ps between snapshots, so this is unit for lagtimes")
    parser.add_argument("--dv", dest="dv", default=0.5,   # in kBT, T is parameter temperature
                        type=float,
                        help="potential Monte Carlo move width")
    parser.add_argument("--dw", dest="dw", default=0.5,
                        type=float,
                        help="log(diffusion) Monte Carlo move width")
    parser.add_argument("--dwrad", dest="dwrad", default=0.5,
                        type=float,
                        help="log(diffusion) Monte Carlo move width")
    parser.add_argument("--D0", dest="D0", default="1.",
                        type=float,
                        help="first guess D0")

    parser.add_argument("--model", dest="model",default="Model",
                        help="set model, default is individual points")

    parser.add_argument("--nmc_update", dest="nmc_update", default=100,
                        type=float,
                        help="number of moves between Monte Carlo step width/temp adjustments (0 if no adjustment)")

    parser.add_argument("-s","--seed", dest="seed", default=None,
                        type=int,
                        help="SEED of the random generator")

    parser.add_argument("--ncosF", dest="ncosF", default=0,
                        type=int,
                        help="Switches basis set of cosinus' on, for the free energy profile. NCOSF is the number of basis set functions.")
    parser.add_argument("--ncosD", dest="ncosD", default=0,
                        type=int,
                        help="Switches basis set of cosinus' on, for the diffusion profile. NCOSD is the number of basis set functions.")
    parser.add_argument("--ncosDrad", dest="ncosDrad", default=0,
                        type=int,
                        help="Switches basis set of cosinus' on, for the radial diffusion profile. NCOSDRAD is the number of basis set functions.")

    parser.add_argument("-k", dest="k", default=-1,
                        type=float,
                        help="spring constant to keep D profile smoother")
    parser.add_argument("--t0", dest="move_timezero", default=False,
                        action="store_true",
                        help="Also make the time offset a variable.")
    parser.add_argument("--dt0", dest="dtimezero", default=0.1,   # in ps
                        type=float,
                        help="time offset (timezero t0) Monte Carlo move width")

    parser.add_argument("--rad", dest="lmax", default=-1,   # in ps
                        type=int,

                        help="Solve radial diffusion equation with LMAX Bessel functions")

    parser.add_argument("--reduction", dest="reduction", default=False,
                        action="store_true",
                        help="this keyword reduces the transition matrix by deleting zero rows/columns before starting the Monte Carlo")
    parser.set_defaults(func=run)


def plot(options):
    print("options:")
    print(options.__dict__)
    print("="*20)

    if options.outfile is None:
        options.outfile = "all"

    options.grey = False #True   # TODO make this optional

    figname = options.outfile
    if options.ave: figname += "_ave"

    F,D,edges,Fst,Dst = read_many_profiles(options.profile_files,pic=options.pic)
    if options.do_rad:
       Drad,redges,Dradst = read_many_profiles_Drad(options.profile_files,pic=options.pic)
    else:
       Drad = [None]
       Dradst = [None]

    make_plots(F,D,Drad,edges,figname,pbc=options.pbc,
           legend=range(len(options.profile_files)),
           grey=options.grey,
           title=options.title,error=[Fst,Dst,Dradst],
           ave=options.ave,
           transparent=options.transparent)


def parse_plot(parser):
    parser.add_argument("profile_files", nargs='+')
    parser.add_argument("-o","--outfile", dest="outfile", default=None,
                      help="basename FILE of the figures with the free energy and diffusion constant profiles")
    parser.add_argument("--ave", dest="ave", default=False,
                      action="store_true",
                      help="whether to plot the averages of the list of filenames as well")
    parser.add_argument("-t", dest="title", default=None,
                      help="TITLE will be added to the title of the plots")
    parser.add_argument("--rad", dest="do_rad", default=False,
                      action='store_true',
                      help="whether to plot the radial diffusion coefficient")
    parser.add_argument("--pic", dest="pic", default=False,
                      action='store_true',
                      help="whether to plot the information in a Pickled Object (logger)")
    parser.add_argument("--transparent", dest="transparent", default=False,
                      action='store_true',
                      help="whether to save a transparent plot")
    parser.add_argument("--nopbc", dest="pbc", default=True,
                      action='store_false',
                      help="plot the profiles only once (instead of twice when periodic boundaries are used)")
    parser.set_defaults(func=plot)


def chm(args):
    assert os.path.isfile(args.config_file), "Config file not found."
    print("Starting mcdiff chm with configuration from {}".format(args.config_file))
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(args.config_file)
    charmm.process_all(config)


def parse_chm(parser):
    parser.add_argument("config_file")
    parser.set_defaults(func=chm)


def define_version(parser):
    parser.add_argument("--version", action='version', version="0.1.0")


def main():
    main_parser = ArgumentParser()
    define_version(main_parser)
    subparsers = main_parser.add_subparsers(title="subcommands", description="")
    parse_run(subparsers.add_parser("run"))
    parse_plot(subparsers.add_parser("plot"))
    parse_chm(subparsers.add_parser("chm"))
    args = main_parser.parse_args()
    args.func(args)


# ================= SUPPORT OLD COMMAND LINE INTERFACE ==============

def run_mcdiff():
    main_parser = ArgumentParser()
    define_version(main_parser)
    parse_run(main_parser)
    args = main_parser.parse_args()
    run(args)


def plotresults():
    main_parser = ArgumentParser()
    define_version(main_parser)
    parse_plot(main_parser)
    args = main_parser.parse_args()
    plotresults(args)
