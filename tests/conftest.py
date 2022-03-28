import panda3d.core as p3d
from direct.showbase.ShowBase import ShowBase
import pytest

PRC_BASE = """
window-type offscreen
framebuffer-hardware false
gl-debug true
audio-library-name null
"""

#pylint:disable=redefined-outer-name

@pytest.fixture
def showbase(request):
    extra_prc = request.param if hasattr(request, 'param') else ''
    print(extra_prc)
    p3d.load_prc_file_data('', f'{PRC_BASE}\n{extra_prc}')
    showbase = ShowBase()
    yield showbase
    showbase.destroy()
