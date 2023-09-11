import argparse
import json
from pathlib import Path
import multiprocessing as mp

import gribscan
from .magician import MAGICIANS


def create_index():
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", metavar="GRIB", help="source gribfile(s)", nargs="+")
    parser.add_argument(
        "-n",
        "--nprocs",
        help="number of parallel processes",
        type=int,
        default=1,
        nargs="?",
    )
    args = parser.parse_args()

    if args.nprocs == 1:
        import ipdb
        with ipdb.launch_ipdb_on_exception():
            [gribscan.write_index(source) for source in args.sources]
    else:
        with mp.Pool(args.nprocs) as pool:
            pool.map(gribscan.write_index, args.sources)


def build_dataset():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "indices",
        metavar="GRIB.index",
        help="source index files (JSONLines)",
        nargs="+",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="outdir",
        default=".",
        help="output directory to write reference filesystems (JSON)",
        type=str,
    )
    parser.add_argument(
        "--prefix",
        metavar="template_prefix",
        default=None,
        help="Absolute path to the location of the dataset",
        type=str,
    )
    parser.add_argument(
        "-m",
        "--magician",
        metavar="magician",
        default="monsoon",
        help="use this magician for dataset assembly",
        type=str,
    )
    args = parser.parse_args()

    if args.prefix is None:
        args.prefix = Path(args.indices[0]).parent.resolve().as_posix() + "/"

    magician = MAGICIANS[args.magician]()

    refs = gribscan.grib_magic(
        args.indices, magician=magician, global_prefix=args.prefix
    )

    for dataset, ref in refs.items():
        fp = Path(f"{args.output}/{dataset}.json")
        fp.parent.mkdir(exist_ok=True, parents=True)
        with open(fp, "w") as indexfile:
            json.dump(ref, indexfile)
