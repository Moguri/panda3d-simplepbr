import logging
import os
import shutil

import setuptools
from setuptools.command.install import install


class BundleShaders(setuptools.Command):
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        installcmd = self.distribution.get_command_obj('install')
        builddir = os.path.join(installcmd.root, 'simplepbr')

        logging.info('Bundling shaders')
        shaderdir = os.path.join(builddir, 'shaders')
        shaders = {}
        for shaderpath in os.listdir(shaderdir):
            with open(os.path.join(shaderdir, shaderpath), encoding='utf8') as shaderfile:
                shaders[shaderpath] = shaderfile.read()
        with open(os.path.join(builddir, 'shaders.py'), 'w', encoding='utf8') as shaderfile:
            shaderfile.write(f'shaders={repr(shaders)}')
        shutil.rmtree(shaderdir)

        logging.info('Bundling textures')
        texturedir = os.path.join(builddir, 'textures')
        textures = {}
        for texpath in os.listdir(texturedir):
            with open(os.path.join(texturedir, texpath), 'rb') as texfile:
                textures[texpath] = texfile.read()
        with open(os.path.join(builddir, 'textures.py'), 'w', encoding='utf8') as texfile:
            texfile.write(f'textures={repr(textures)}')
        shutil.rmtree(texturedir)

install.sub_commands.append(('bundle_shaders', None))

setuptools.setup(
    cmdclass={'bundle_shaders': BundleShaders}
)
