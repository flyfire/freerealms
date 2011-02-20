#!/bin/sh

echo 'HGVERSION = 0x'`hg --debug id -i` > version.py

