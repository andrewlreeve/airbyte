#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_cin7_core import SourceCin7Core

if __name__ == "__main__":
    source = SourceCin7Core()
    launch(source, sys.argv[1:])
