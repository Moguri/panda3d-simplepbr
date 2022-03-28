import pytest #pylint:disable=wrong-import-order

import simplepbr

@pytest.mark.parametrize('showbase', ['', 'gl-version 3 2'], indirect=True)
@pytest.mark.parametrize('use_normal_maps', [False, True])
@pytest.mark.parametrize('enable_shadows', [False, True])
@pytest.mark.parametrize('enable_fog', [False, True])
@pytest.mark.parametrize('use_occlusion_maps', [False, True])
@pytest.mark.parametrize('use_emission_maps', [False, True])
@pytest.mark.parametrize('use_hardware_skinning', [False, True])
def test_setup(showbase,
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
        use_normal_maps=use_normal_maps,
        enable_shadows=enable_shadows,
        enable_fog=enable_fog,
        use_occlusion_maps=use_occlusion_maps,
        use_emission_maps=use_emission_maps,
        use_hardware_skinning=use_hardware_skinning,
    )

    pipeline.verify_shaders()
