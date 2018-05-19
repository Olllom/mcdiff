"""
A module to do the full Bayesian analysis using Rick's modified CHARMM version
for creating transition matrices.
"""

from __future__ import print_function

import multiprocessing
from functools import partial
from itertools import product
import subprocess
import os
import random
import shutil
import warnings


def tmat_file(config, sim_id, lag_time):
    """
    Name of the file containing a transition matrix.
    """
    return os.path.abspath(
        config.get("charmm","tmat").format(sim_id, lag_time))


def profiles_file(config, sim_id, lag_time, task):
    """
    Name of the file containing density and free energy profiles.
    """
    return os.path.abspath(os.path.join(
        config.get("general","output_dir"),
        "profiles.{}.{}.{}.dat".format(sim_id, lag_time, task)
    ))


def log_file(config, sim_id, lag_time, task):
    return os.path.abspath(os.path.join(
        config.get("general","output_dir"),
        "profiles.{}.{}.{}.log".format(sim_id, lag_time, task)
    ))

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

    # apply equilibration settings to production
    tmp = opts["equilibration"].copy()
    tmp.update(opts["production"])
    opts["production"] = tmp

    # get filenames
    tmat_in = tmat_file(config, sim_id, lag_time)
    equi_out = profiles_file(config, sim_id, lag_time, 0)
    prod_out = profiles_file(config, sim_id, lag_time, 1)
    equi_log = log_file(config, sim_id, lag_time, 0)
    prod_log = log_file(config, sim_id, lag_time, 1)

    # run equilibration
    if not os.path.isfile(equi_out):
        print("Starting MC Equilibration {} {}...".format(sim_id, lag_time))
        call_args = ["mcdiff", "run", tmat_in, "-o", equi_out]
        for key in opts["equilibration"]:
            call_args += [key, opts["equilibration"][key]]
        with open(equi_log, "w") as f:
            subprocess.call(call_args, stdout=f, stderr=subprocess.STDOUT)
        assert os.path.isfile(equi_out), \
            ("Something went wrong in mcdiff equilibration run. "
             "Check output in {}.".format(equi_log))
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
        with open(prod_log, "w") as f:
            subprocess.call(call_args, stdout=f, stderr=subprocess.STDOUT)
        assert os.path.isfile(prod_out), \
            ("Something went wrong in mcdiff production run. "
             "Check output in {}.".format(prod_log))
        print("Production for {} {} finished.".format(sim_id, lag_time))
    else:
        print("Production file {} found. Not updating.".format(equi_out))
    assert os.path.exists(prod_out)

    return prod_out


def make_transition_matrices_charmm(sim_id, config):
    """
    Wrapper for the CHARMM command to extract the transition matrix.
    config: ConfigParser Instance

    Args:
        config: ConfigParser instance.
        sim_id: ID of the replica.
    """
    # get lag times
    lag_start = int(config.get("general", "lag_start"))
    lag_end = int(config.get("general", "lag_end"))
    lag_inc = int(config.get("general", "lag_inc"))
    lagtimes = range(lag_start, lag_end+1, lag_inc)
    # pass, if all transition matrices exists
    if all(os.path.isfile(tmat_file(config, sim_id, lt)) for lt in lagtimes):
        print("Transition matrices for {} exists. Not updating.".format(sim_id))
    # get charmm info from config file
    print("Assembling transition matrices from charmm command:")
    traj, firstfr, lastfr = eval(config.get("general", "trajectories"))[sim_id]
    exedir = eval(config.get("charmm", "exe_dirs"))[sim_id]
    executable = config.get("charmm", "executable")
    script = config.get("charmm", "script")
    # call charmm
    #  -- this in an awkward workaround for charmm not allowing to write to mixed-case filenames --
    tmp_tmat = os.path.join("/tmp", str(random.random()))
    command = "{} FF:{} LF:{} FL:{} LL:{} IL:{} TRJ:{} TMAT:{}".format(
        executable, firstfr, lastfr, lag_start, lag_end, lag_inc,
        os.path.abspath(traj), tmp_tmat)
    print("...", command)
    outfile = os.path.join(config.get("general","output_dir"),
                           "chm_tmat.{}.out".format(sim_id))
    with open(outfile,"w") as stdout:
        with open(script,"r") as stdin:
            p = subprocess.Popen(command.strip().split(),
                                 stdin=stdin,
                                 stdout=stdout,
                                 stderr=subprocess.STDOUT,
                                 cwd=os.path.abspath(exedir)
                                 )
            p.communicate()
            rc = p.returncode
            if rc != 0:
                warnings.warn("Something might have gone wrong while executing "
                             "the charmm script. Check for errors in "
                             "{}".format(outfile))
    for lt in lagtimes:
        tmp = "{}_{}".format(tmp_tmat, lt)
        assert os.path.isfile(tmp), ("Could not find output files from CHARMM."
                                     "Check for errors in CHARMM output: "
                                     "{}".format(outfile))
        shutil.move(tmp, tmat_file(config, sim_id, lt))
    print("Transition matrices for {} assembled:", sim_id)


def process_one_lag_time(index, id_lag_pairs, config):
    sim_id, lag_time = id_lag_pairs[index]
    run_mcdiff_one_tmat(config, sim_id, lag_time)


def process_all(config):
    """
    Create transition matrices and run Bayesian analysis for one simulation.
    Parallelize over simulation ids and lag times.
    Args:
        config: A ConfigParser object.
        traj_file: Trajectory
    """
    # make output directory
    parallel = config.getboolean("general", "parallel")
    outdir = config.get("general", "output_dir")
    if not os.path.isdir(outdir):
        os.mkdir(outdir)

    # create matrices (parallelize over sim_ids)
    sim_ids = eval(config.get("general", "trajectories")).keys()
    mk_matrices = partial(make_transition_matrices_charmm, config=config)
    if parallel:
        pool = multiprocessing.Pool(len(sim_ids))
        pool.map(mk_matrices, sim_ids)
        pool.close()
        pool.join()
    else:
        for id in range(sim_ids):
            mk_matrices(id)

    # run mcdiff (parallelize over sim_ids and lag times)
    lag_start = int(config.get("general", "lag_start"))
    lag_end = int(config.get("general", "lag_end"))
    lag_inc = int(config.get("general", "lag_inc"))
    lag_times = range(lag_start, lag_end+1, lag_inc)
    # helper function to give the processes to a pool of workers
    pairs = tuple(product(sim_ids, lag_times))
    proc_one_lag = partial(process_one_lag_time, id_lag_pairs=pairs, config=config)
    if parallel:
        pool = multiprocessing.Pool(len(pairs))
        pool.map(proc_one_lag, range(len(pairs)))
        pool.close()
        pool.join()
    else:
        for i in range(len(pairs)):
            proc_one_lag(i)
    print("")
    print("="*50)
    print(" "*10, "Command mcdiff chm finished.")
    print("=" * 50)


