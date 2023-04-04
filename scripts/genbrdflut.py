#!/usr/bin/env python
import os

import panda3d.core as p3d

from simplepbr import _ibl_funcs as ibl

def main():
    brdflut = ibl.gen_brdf_lut(512, num_samples=1024)
    outfile = p3d.Filename.from_os_specific(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'simplepbr',
            'textures',
            'brdf_lut.txo'
        )
    )
    brdflut.write(outfile)

if __name__ == '__main__':
    main()
