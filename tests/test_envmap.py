import os
import time

import panda3d.core as p3d

import simplepbr


ASSETDIR = p3d.Filename.from_os_specific(
    os.path.join(os.path.dirname(__file__), 'assets')
)


def test_envmap_bam_read():
    envmap = simplepbr.EnvMap.from_file_path(ASSETDIR / 'hdri' / 'cubemap.env')
    assert envmap
    assert envmap.cubemap
    assert envmap.sh_coefficients[0] != p3d.LVector3(0, 0, 0)


def test_envmap_bam_write(tmpdir):
    envmap = simplepbr.EnvMap.create_empty()
    while not envmap.is_prepared.done():
        p3d.AsyncTaskManager.get_global_ptr().poll()
        time.sleep(1)

    outpath = tmpdir / 'cubemap.env'
    envmap.write(outpath)
    assert os.path.exists(outpath)
