import glob
import json
import logging
import textwrap
from functools import partial
from pathlib import Path
import multiprocessing as mp

import click

import gribscan
from .magician import MAGICIANS


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Increase the logging level.")
def cli(verbose):
    """gribscan: Index and build GRIB datasets."""
    logging.basicConfig()
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command("index")
@click.argument("sources", nargs=-1, type=click.Path(exists=True))
@click.option(
    "-o",
    "--outdir",
    type=click.Path(file_okay=False, writable=True),
    default=None,
    help="Output directory to write index files.",
)
@click.option("-f", "--force", is_flag=True, help="Overwrite existing index files.")
@click.option(
    "-n",
    "--nprocs",
    type=int,
    default=1,
    show_default=True,
    help="Number of parallel processes.",
)
def create_index(sources, outdir, force, nprocs):
    """Create index files from GRIB sources."""
    mapfunc = partial(gribscan.write_index, outdir=outdir, force=force)
    with mp.Pool(nprocs) as pool:
        pool.map(mapfunc, sources)


@cli.command("build")
@click.argument("indices", nargs=-1, type=click.Path(exists=True))
@click.option(
    "-g",
    "--glob",
    "glob_pattern",
    type=str,
    help="Glob pattern to create list of index files (JSONLines).",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=False, writable=True),
    default=".",
    show_default=True,
    help="Output directory to write reference filesystems (JSON).",
)
@click.option(
    "--prefix",
    type=str,
    help=textwrap.dedent(
        """\
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
)
@click.option(
    "-m",
    "--magician",
    default="monsoon",
    show_default=True,
    type=click.Choice(MAGICIANS.keys()),
    help="Magician to use for dataset assembly.",
)
def build_dataset(indices, glob_pattern, output, prefix, magician):
    """Build dataset references from index files."""
    if not glob_pattern and not indices:
        raise click.UsageError("You must provide either a glob pattern or a file list.")
    if glob_pattern and indices:
        raise click.UsageError("Cannot provide both glob pattern and file list.")

    if glob_pattern:
        indices = list(glob.iglob(glob_pattern))

    magician_instance = MAGICIANS[magician]()
    refs = gribscan.grib_magic(
        indices, magician=magician_instance, global_prefix=prefix
    )

    Path(output).mkdir(parents=True, exist_ok=True)
    for dataset, ref in refs.items():
        with open(Path(output) / f"{dataset}.json", "w") as f:
            json.dump(ref, f, indent=2)


if __name__ == "__main__":
    cli()
