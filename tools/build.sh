#!/bin/sh
# builds the LZX ROM-file decompressor used by extract_all.py
cc -O2 -w -I. -o romfile romfile.c lzxd.c && echo "built romfile"
