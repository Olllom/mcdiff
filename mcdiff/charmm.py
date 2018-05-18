"""
A module to do the full Bayesian analysis using Rick's modified CHARMM version
for creating transition matrices.
"""

from __future__ import print_function

import multiprocessing
import subprocess
import os

import cli


def tmat_file(config, sim_id, lag_time):
    """
    Name of the file containing a transition matrix.
    """
    return config.get("charmm","tmat").format(sim_id, lag_time)


def profiles_file(config, sim_id, lag_time, task):
    """
    Name of the file containing density and free energy profiles.
    """
    return os.path.join(
        config.get("general","output_dir"),
        "profiles.{}.{}.{}.dat".format(sim_id, lag_time, task)
    )


def run_mcdiff_one_tmat(config, sim_id, lag_time):
    """
    Run Monte-Carlo procedure (equilibration and production)
    for one transition matrix.
    """
    # get opts from config file
    opts = {}
    for run in ["equilibration", "production"]:
        opts[run] = {opt: config.get(run, opt)
                     for opt in config.options(run)}
        # add dashes
        for key in opts[run]:
            dash = "-" if len(key) == 1 else "--"
            opts[run][dash+key] = opts[run].pop(key)
    # apply equilibration settings to production
    tmp = opts["equilibration"].copy()
    tmp.update(opts["production"])
    opts["production"] = tmp

    # get filenames
    tmat_in = tmat_file(config, sim_id, lag_time)
    equi_out = profiles_file(config, sim_id, lag_time, 0)
    prod_out = profiles_file(config, sim_id, lag_time, 1)

    # run equilibration
    if not os.path.isfile(equi_out):
        print("Starting MC Equilibration {} {}...".format(sim_id, lag_time))
        call_args = ["mcdiff", "run", tmat_in, "-o", equi_out]
        for key in opts["equilibration"]:
            call_args += [key, opts["equilibration"][key]]
        cli.main(call_args)
        print("Equilibration for {} {} finished.".format(sim_id, lag_time))
    else:
        print("Equilibration file {} found. Not updating.".format(equi_out))
    assert os.path.exists(equi_out)

    # run production
    if not os.path.isfile(prod_out):
        print("Starting MC Production {} {}...".format(sim_id, lag_time))
        call_args = ["mcdiff", "run", tmat_in, "-o", prod_out,
                     "--initf", equi_out]
        for key in opts["production"]:
            call_args += [key, opts["production"][key]]
        cli.main(call_args)
        print("Production for {} {} finished.".format(sim_id, lag_time))
    else:
        print("Production file {} found. Not updating.".format(equi_out))
    assert os.path.exists(prod_out)

    return prod_out


def make_transition_matrix_charmm(config, sim_id, lag_time):
    """
    Wrapper for the CHARMM command to extract the transition matrix.
    config: ConfigParser Instance

    Args:
        config: ConfigParser instance.
        sim_id: ID of the replica.
        lag_time: .

    Returns:
        Filename of the transition matrix.
    """
    # pass, if transition matrix exists
    tmat = tmat_file(config, sim_id, lag_time)
    if os.path.isfile(tmat):
        print("Transition matrix {} exists. Not updated.".format(tmat))
        return tmat
    # get info from config file
    traj, firstfr, lastfr = eval(config.get("general", "trajectories"))[sim_id]
    executable = config.get("charmm", "executable")
    script = config.get("charmm", "script")
    environment = {
        "TRAJECTORY": traj
    }
    # call charmm
    command = "{} FF:{} LF:{} LAG:{}".format(
        executable, firstfr, lastfr, lag_time)
    outfile = os.path.join(config.get("general","output_dir"),
                           "chm_tmat.{}.{}.out".format(sim_id, lag_time))
    with open(outfile,"w") as stdout:
        with open(script,"r") as stdin:
            p = subprocess.Popen(command.strip().split(),
                                 env=environment, stdin=subprocess.PIPE,
                                 stdout=stdout,
                                 stderr=subprocess.STDOUT
                                 )
            p.communicate(input=stdin)
            rc = p.returncode()
            assert rc == 0
    assert os.path.isfile(tmat)
    return tmat


def process_one_lag_time(config, sim_id, lag_time):
    make_transition_matrix_charmm(config, sim_id, lag_time)
    run_mcdiff_one_tmat(config, sim_id, lag_time)


def process_one_replica(config, sim_id):
    """
    Create transition matrices and run Bayesian analysis for one simulation
    (thread-parallelism).
    Args:
        config: A ConfigParser object.
        traj_file: Trajectory
    """
    lag_times = config.get("general", "lag_times").strip().split(",")
    lag_times = [int(lt) for lt in lag_times]
    pool = multiprocessing.Pool(len(lag_times))
    pool.map(process_one_lag_time,
             ((config, sim_id, lt) for lt in lag_times))
    pool.join()


def process_all(config):
    sim_ids = eval(config.get("general", "trajectories")).keys()
    pool = multiprocessing.Pool(len(sim_ids))
    pool.map(process_one_replica,
             ((config, id) for id in sim_ids))
    pool.join()


