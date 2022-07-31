import os
import sys
import logging

logger = logging.getLogger("pytest")

DIR = os.path.dirname(os.path.realpath(__file__))
temp_path = [os.path.dirname(DIR)]
temp_path.extend(sys.path)
sys.path = temp_path

import varvault


class Keyring(varvault.Keyring):
    key_valid_type_is_str = varvault.Key("key_valid_type_is_str", valid_type=str)
    key_valid_type_is_int = varvault.Key("key_valid_type_is_int", valid_type=int)

