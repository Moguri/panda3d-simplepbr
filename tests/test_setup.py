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
    )
    return ShowBase()


def test_setup(showbase):
    simplepbr.init(
        render_node=showbase.render,
        window=showbase.win,
        camera_node=showbase.cam,
    )
