#!/usr/bin/env python3
import pathlib

open_path = pathlib.Path("/etc/")
for child in open_path.iterdir():
    print(child)
