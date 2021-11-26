import glob
import pathlib
import re

from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = pathlib.Path(f"{HERE}/README.md").read_text()

# Version handling
MAJOR = 1  # Change this if the previous MAJOR is incompatible with this build. Set MINOR and PATCH to 0
MINOR = 1  # Change this if the functionality has changed, but we are still backwards compatible with previous MINOR versions. Set PATCH to 0
PATCH = 4  # Change this is if we are fixing a bug that doesn't change the functionality. If a bug fix has caused functionality to be changed, see MINOR instead
VERSION = f"{MAJOR}.{MINOR}.{PATCH}"


def find_todos_for_version_in_code():
    """
    Checks for TODOs/FIXMEs in the code linked to the current version
    :return: A list of lines in the code that are marked with FIX ME or TO DO linked to the current version.
    """
    """This pattern should match these lines (given VERSION is 2.0.0): 
    some_code = "code"  # FIXME: Remove this in 2.0.0
    # TODO: Remove this in 2.0.0
    # fixme: Remove this in 2.0.0
    # todo: Remove this in 2.0.0
    # fix me: Remove this in 2.0.0
    # to do: Remove this in 2.0.0
    """
    pattern = re.compile(rf".*(\#.*(?:[Ff][Ii][Xx].*[Mm][Ee]|[Tt][Oo].*[Dd][Oo]).*{MAJOR}\.{MINOR}\.{PATCH}.*)")
    files = glob.glob("varvault/*.py")
    matches = list()
    for file in files:
        with open(file) as f:
            for i, line in enumerate(f.readlines()):
                match = re.match(pattern, line)
                if match:
                    matches.append((file, i, match.group(1)))
    return matches


todos_in_code = find_todos_for_version_in_code()
assert len(todos_in_code) == 0, f"There are FIXMEs/TODOs in the code that appear to be linked to this version; You should fix these before making the release: {todos_in_code}"


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
