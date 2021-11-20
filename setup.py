import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = pathlib.Path(f"{HERE}/README.md").read_text()

# Version handling
MAJOR = 1  # Change this if the previous MAJOR is incompatible with this build. Set MINOR and PATCH to 0
MINOR = 1  # Change this if the functionality has changed, but we are still backwards compatible with previous MINOR versions. Set PATCH to 0
PATCH = 1  # Change this is if we are fixing a bug that doesn't change the functionality. If a bug fix has caused functionality to be changed, see MINOR instead
VERSION = f"{MAJOR}.{MINOR}.{PATCH}"

# This call to setup() does all the work
setup(
    name="varvault",
    version=VERSION,
    description="A package that sets up a key-value vault to store and access variables in a global context.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/data-ductus/varvault",
    author="Calle Holst",
    author_email="calle.holst@dataductus.se",
    license="Apache 2.0",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8"
    ],
    packages=["varvault"],
    include_package_data=True,
)
