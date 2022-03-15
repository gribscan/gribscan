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
    parser.add_argument("-o", "--output", metavar="refs.json", default="refs.json", help="reference filesystem specification (JSON)", type=str)
    parser.add_argument("--prefix", metavar="template_prefix", default=None, help="Absolute path to the location of the dataset", type=str)
    args = parser.parse_args()

    if args.prefix is None:
        args.prefix  = Path(args.indices[0]).parent.resolve().as_posix() + "/"

    refs = gribscan.grib_magic(args.indices, global_prefix=args.prefix)

    with open(args.output, "w") as indexfile:
        json.dump(refs, indexfile)
