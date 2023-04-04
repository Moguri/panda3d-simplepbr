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
        installcmd = self.distribution.get_command_obj('install')
        builddir = os.path.join(installcmd.root, 'simplepbr')

        log.info('Bundling shaders')
        shaderdir = os.path.join(builddir, 'shaders')
        shaders = {}
        for shaderpath in os.listdir(shaderdir):
            with open(os.path.join(shaderdir, shaderpath)) as shaderfile:
                shaders[shaderpath] = shaderfile.read()
        with open(os.path.join(builddir, 'shaders.py'), 'w') as shaderfile:
            shaderfile.write(f'shaders={repr(shaders)}')
        shutil.rmtree(shaderdir)

        log.info('Bundling textures')
        texturedir = os.path.join(builddir, 'textures')
        textures = {}
        for texpath in os.listdir(texturedir):
            with open(os.path.join(texturedir, texpath), 'rb') as texfile:
                textures[texpath] = texfile.read()
        with open(os.path.join(builddir, 'textures.py'), 'w') as texfile:
            texfile.write(f'textures={repr(textures)}')
        shutil.rmtree(texturedir)

install.sub_commands.append(('bundle_shaders', None))

setuptools.setup(
    cmdclass={'bundle_shaders': BundleShaders}
)
