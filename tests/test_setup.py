import panda3d.core as p3d
import pytest #pylint:disable=wrong-import-order

import simplepbr

#pylint:disable=redefined-outer-name
#pylint:disable=import-outside-toplevel


@pytest.fixture(scope='session')
def showbase():
    from direct.showbase.ShowBase import ShowBase
    p3d.load_prc_file_data(
        '',
        'window-type offscreen\n'
        'framebuffer-hardware false\n'
        'gl-debug true\n'
    )
    return ShowBase()


def test_setup(showbase):
    pipeline = simplepbr.init(
        render_node=showbase.render,
        window=showbase.win,
        camera_node=showbase.cam,
        use_normal_maps=True,
        enable_shadows=True,
        enable_fog=True,
        use_occlusion_maps=True,
    )

    pipeline.verify_shaders()
