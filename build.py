#!/usr/bin/env python

from subprocess import Popen, PIPE

hgversion = Popen(["hg", "--debug", "id", "-i"], stdout=PIPE).communicate()[0]
with open('version.py', 'w') as f:
    f.write('HGVERSION = 0x%s\n' % hgversion)

