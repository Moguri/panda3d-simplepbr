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


@pytest.mark.parametrize('use_330', [False, True])
@pytest.mark.parametrize('use_normal_maps', [False, True])
@pytest.mark.parametrize('enable_shadows', [False, True])
@pytest.mark.parametrize('enable_fog', [False, True])
@pytest.mark.parametrize('use_occlusion_maps', [False, True])
@pytest.mark.parametrize('use_emission_maps', [False, True])
@pytest.mark.parametrize('use_hardware_skinning', [False, True])
def test_setup(showbase,
               use_330,
               use_normal_maps,
               enable_shadows,
               enable_fog,
               use_occlusion_maps,
               use_emission_maps,
               use_hardware_skinning):
    pipeline = simplepbr.init(
        render_node=showbase.render,
        window=showbase.win,
        camera_node=showbase.cam,
        use_330=use_330,
        use_normal_maps=use_normal_maps,
        enable_shadows=enable_shadows,
        enable_fog=enable_fog,
        use_occlusion_maps=use_occlusion_maps,
        use_emission_maps=use_emission_maps,
        use_hardware_skinning=use_hardware_skinning,
    )

    pipeline.verify_shaders()
