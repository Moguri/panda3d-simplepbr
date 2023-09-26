import os

import panda3d.core as p3d

import simplepbr


def test_save_sdr_lut(showbase, tmp_path):
    simplepbr.utils.sdr_lut_screenshot(showbase, namePrefix=tmp_path.as_posix())

def test_load_sdr_lut():
    filepath = p3d.Filename(os.path.dirname(__file__), 'lut.png')
    simplepbr.utils.load_sdr_lut(filepath)
