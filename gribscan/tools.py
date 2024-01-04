import argparse
import glob
import json
import textwrap
from functools import partial
from pathlib import Path
import multiprocessing as mp

import gribscan
from .magician import MAGICIANS


def create_index():
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", metavar="GRIB", help="source gribfile(s)", nargs="+")
    parser.add_argument(
        "-o",
        "--outdir",
        help="output directory to write index files",
        type=str,
        default=None,
        nargs="?",
    )
    parser.add_argument(
        "-f",
        "--force",
        help="overwrite existing index files",
        action="store_true",
    )
    parser.add_argument(
        "-n",
        "--nprocs",
        help="number of parallel processes",
        type=int,
        default=1,
        nargs="?",
    )
    args = parser.parse_args()

    mapfunc = partial(gribscan.write_index, outdir=args.outdir, force=args.force)
    with mp.Pool(args.nprocs) as pool:
        pool.map(mapfunc, args.sources)


def build_dataset():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "indices",
        metavar="GRIB.index",
        help="source index files (JSONLines)",
        nargs="*",
    )
    parser.add_argument(
        "-g",
        "--glob",
        metavar="GLOB.index",
        help="glob pattern to create list of index files (JSONLines)",
        type=str,
        nargs="?",
        default=None,
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
        help=textwrap.dedent("""\
            Absolute path to the location of the dataset.

            The prefix is prepended to the filename stored in the index files.
            For full file paths, a sub-tree can be denoted using the '/./'
            character. The following examples show how a prefix adds to
            different filenames:

            /prefix/ + filename.grb = /prefix/filename.grb
            /prefix/ + path/filename.grb = /prefix/path/filename.grb
            /prefix/ + path/./sub/tree/filename.grb = /prefix/sub/tree/filename.grb
        """
        ),
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

    magician = MAGICIANS[args.magician]()

    if args.glob is None and not args.indices:
        parser.error("You need to pass a glob pattern or a file list.")

    if args.glob is not None and args.indices:
        parser.error("It is not possible to pass a glob pattern and a file list.")

    if args.glob is not None:
        indices = glob.iglob(args.glob)

    if args.indices:
        indices = args.indices

    refs = gribscan.grib_magic(
        indices, magician=magician, global_prefix=args.prefix
    )

    for dataset, ref in refs.items():
        with open(f"{args.output}/{dataset}.json", "w") as indexfile:
            json.dump(ref, indexfile)
