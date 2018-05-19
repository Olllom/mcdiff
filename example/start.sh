#! /bin/bash

# Assuming you have the following modules loaded...
##### module load intel/18.0.1
##### module load anaconda3/4.2.0

# ... and an active python-2.7 conda environment...
##### conda create --name mcdiff_py27 python=2.7
##### source activate mcdiff_py27

# ... you can install the code like this...
##### cd ..
##### python setup.py install

# ... and use it as follows:
##### cd -

mcdiff chm psm_test.cfg

