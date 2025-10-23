from gribscan.gribscan import *


try:
    # the ._version module should be created by setuptools_scm
    from ._version import __version__, __version_tuple__
except ImportError:
    # fallback if it's not there (e.g. package not properly installed)
    __version__ = "unknown"
    __version__tuple__ = ()
