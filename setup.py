import os
import shutil

from distutils.command.install import install
from distutils import log
import setuptools


class BundleShaders(setuptools.Command):
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        log.info('Bundling shaders')
        installcmd = self.distribution.get_command_obj('install')
        builddir = os.path.join(installcmd.root, 'simplepbr')
        shaderdir = os.path.join(builddir, 'shaders')
        shaders = {}
        for shaderpath in os.listdir(shaderdir):
            with open(os.path.join(shaderdir, shaderpath)) as shaderfile:
                shaders[shaderpath] = shaderfile.read()
        with open(os.path.join(builddir, 'shaders.py'), 'w') as shaderfile:
            shaderfile.write(f'shaders={repr(shaders)}')
        shutil.rmtree(shaderdir)

install.sub_commands.append(('bundle_shaders', None))

setuptools.setup(
    cmdclass={'bundle_shaders': BundleShaders}
)
