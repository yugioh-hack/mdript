#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GUI をダブルクリックで起動するための入口。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mdript.gui import main

if __name__ == "__main__":
    sys.exit(main())
