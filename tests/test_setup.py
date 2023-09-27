import pytest #pylint:disable=wrong-import-order

import panda3d.core as p3d

import simplepbr

def test_setup_defaults(showbase):
    simplepbr.init(
        render_node=showbase.render,
        window=showbase.win,
        camera_node=showbase.cam,
    )


def test_setup_prc_variables(showbase):
    configpage = p3d.load_prc_file_data(
        '',
        'simplepbr-max-lights 4\n'
        'simplepbr-use-emission-maps f\n'
        'simplepbr-msaa-samples 8\n'
    )
    pipeline = simplepbr.init(
        render_node=showbase.render,
        window=showbase.win,
        camera_node=showbase.cam,
    )

    cpm = p3d.ConfigPageManager.get_global_ptr()
    cpm.delete_explicit_page(configpage)

    assert pipeline.max_lights == 4
    assert not pipeline.use_emission_maps
    assert pipeline.msaa_samples == 8


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
