import glob
import re

from commons import varvault, ROOT_DIR


def test_no_todos_for_version_in_code():
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
    pattern = re.compile(rf".*(#.*(?:[Ff][Ii][Xx].*[Mm][Ee]|[Tt][Oo].*[Dd][Oo]).*{varvault.__version__}.*)")
    files = glob.glob(f"{ROOT_DIR}/varvault/*.py")
    matches = list()
    for file in files:
        with open(file) as f:
            for i, line in enumerate(f.readlines()):
                match = re.match(pattern, line)
                if match:
                    matches.append((file, i, match.group(1)))
    assert len(matches) == 0, f"There are FIXMEs/TODOs in the code that appear to be linked to this version; You should fix these before making the release: {matches}"

