from setuptools import setup, find_packages


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="gribscan",
    version="0.0.1",
    description="create indices for GRIB files and provide an xarray interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "cfgrib",
        "eccodes",
        "numcodecs",
        "numpy",
    ],
    entry_points={
        "numcodecs.codecs": [
            "rawgrib=gribscan.rawgribcodec:RawGribCodec",
            "aec=gribscan.aeccodec:AECCodec",
        ]
    },
)
