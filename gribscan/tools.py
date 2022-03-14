import argparse
import json
from pathlib import Path
import multiprocessing as mp

import gribscan


def create_index():
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", metavar="GRIB", help="source gribfile(s)", nargs="+")
    parser.add_argument("-n", "--nprocs", help="number of parallel processes", type=int, default=1, nargs="?")
    args = parser.parse_args()

    with mp.Pool(args.nprocs) as pool:
        pool.map(gribscan.write_index, args.sources)


def build_dataset():
    parser = argparse.ArgumentParser()
    parser.add_argument("indices", metavar="GRIB.index", help="source index files (JSONLines)", nargs="+")
    parser.add_argument("output", metavar="refs.json", help="reference filesystem specification (JSON)")
    args = parser.parse_args()

    refs = gribscan.grib_magic(args.indices, global_prefix=Path(args.output).parent.resolve().as_posix() + "/")

    with open(args.output, "w") as indexfile:
        json.dump(refs, indexfile)
