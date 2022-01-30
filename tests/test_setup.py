import panda3d.core as p3d
import pytest #pylint:disable=wrong-import-order

import simplepbr

#pylint:disable=redefined-outer-name
#pylint:disable=import-outside-toplevel

PRC_BASE = """
window-type offscreen
framebuffer-hardware false
gl-debug true
audio-library-name null
"""


@pytest.fixture
def showbase(request):
    extra_prc = request.param if hasattr(request, 'param') else ''
    from direct.showbase.ShowBase import ShowBase
    print(extra_prc)
    p3d.load_prc_file_data('', f'{PRC_BASE}\n{extra_prc}')
    showbase = ShowBase()
    yield showbase
    showbase.destroy()


@pytest.mark.parametrize('showbase', ['', 'gl-version 3 2'], indirect=True)
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

    if not pipeline.use_330:
        pipeline.enable_shadows = False

    pipeline.verify_shaders()

def test_hw_skinning_120(showbase):
    pipeline = simplepbr.init(
        render_node=showbase.render,
        window=showbase.win,
        camera_node=showbase.cam,
        use_330=False,
        use_hardware_skinning=True
    )

    pipeline.verify_shaders()
