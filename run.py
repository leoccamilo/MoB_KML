#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Entry point for MoB_KML application."""

import os

os.environ["PANDAS_ARROW_STRING"] = "0"

from cell_kml_generator.main import main

if __name__ == "__main__":
    main()
