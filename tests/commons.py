import os
import sys
import logging

logger = logging.getLogger("pytest")

DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(DIR)
# The following change to sys.path ensures varvault is imported from the source code, not the installed package.
sys.path = [ROOT_DIR] + sys.path


import varvault


class Keyring(varvault.Keyring):
    key_valid_type_is_str = varvault.Key("key_valid_type_is_str", valid_type=str)
    key_valid_type_is_int = varvault.Key("key_valid_type_is_int", valid_type=int)

