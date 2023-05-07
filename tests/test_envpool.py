import os

import panda3d.core as p3d

import simplepbr


ASSETDIR = p3d.Filename.from_os_specific(
    os.path.join(os.path.dirname(__file__), 'assets')
)


def test_envpool_load_str():
    pool = simplepbr.EnvPool.ptr()
    env = pool.load(ASSETDIR / 'hdri' / 'cubemap_#.hdr')

    assert env.cubemap
