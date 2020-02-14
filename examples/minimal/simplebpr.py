import sys

import simplepbr

from panda3d.core import NodePath  # noqa
from panda3d.core import PointLight  # noqa

from direct.showbase.ShowBase import ShowBase


class SimplePbrDemo(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        simplepbr.init()

        self.accept('escape', sys.exit)
        self.accept('f11', self.debug)

        model = loader.load_model("pbrcube.bam")
        model.reparent_to(render)

        # Camera
        self.cam_gimbal = NodePath('gimbal')
        self.cam_gimbal.reparent_to(render)
        base.cam.reparent_to(self.cam_gimbal)
        base.cam.set_pos(0, -10, 0)
        base.cam.look_at(0, 0, 0)
        self.add_task(self.update_camera)

        # Light
        light = PointLight('plight')
        light.set_color((10, 10, 10, 10))
        light.set_attenuation((1, 0, 1))
        light_np = base.cam.attach_new_node(light)
        render.set_light(light_np)
        light_np.set_pos(0, 0, 2)

        # Debug info
        render.ls()
        render.analyze()

    def update_camera(self, task):
        self.cam_gimbal.set_h(self.cam_gimbal, globalClock.dt*30)
        return task.cont

    def debug(self):
        import pdb; pdb.set_trace()


simple_pbr_demo = SimplePbrDemo()
simple_pbr_demo.run()
