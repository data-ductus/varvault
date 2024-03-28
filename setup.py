import pathlib

from setuptools import setup

import varvault

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = pathlib.Path(f"{HERE}/README.md").read_text()


assert varvault.__version__


# This call to setup() does all the work
setup(
    name="varvault",
    version=varvault.__version__,
    description="A package that sets up a key-value vault to store and access variables in a global context.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/data-ductus/varvault",
    author="Chloe Holst",
    author_email="chloe.holst@dataductus.se",
    license="Apache 2.0",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8"
    ],
    packages=["varvault"],
    include_package_data=True,
)
