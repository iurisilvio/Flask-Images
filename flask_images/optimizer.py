# coding: utf-8
import imghdr
import logging
import os
import shutil
from subprocess import PIPE, call

from flask import current_app

logger = logging.getLogger(__name__)


class Optimizer(object):

    _whitelist = set(["gif", "jpeg", "png"])
    _tools = set(['jpegoptim', 'jpegtran', 'gifsicle', 'optipng', 'advpng', 'pngcrush'])

    @property
    def tools(self):
        return current_app.config.get("IMAGES_OPTIMIZE_TOOLS", self._tools)

    def optimize(self, path):
        """
        Returns True if the optimization worked.

        Returns False if `path` is not a file or if some external call failed.
        """
        if not os.path.isfile(path):
            logger.error("'%s' is not a file." % path)
            return False

        if current_app.config.get("IMAGES_DEBUG"):  # Create a copy of original file for debugging purposes
            shutil.copy(path, path + ".orig")

        filetype = imghdr.what(path)
        _command = None
        if filetype in self._whitelist:
            _command = getattr(self, filetype + "_cli")()

        if _command:
            _command = _command % {'file': path}
            try:
                retcode = call(_command, shell=True, stdout=PIPE)
            except:
                logger.exception('Image optimization failed: %s' % _command)
                return False

            if retcode != 0:
                logger.error('Image optimization failed: %s' % _command)
                return False
        return False

    def gif_cli(self):
        """Gifsicle only optimizes animations.

        Eventually add support to change gifs to png8."""
        if "gifsicle" in self.tools:
            return u"gifsicle -O2 --batch '%(file)s'"
        return None

    def jpeg_cli(self):
        """
        Prefer jpegtran to jpegoptim since it makes smaller images
        and can create progressive jpegs (smaller and faster to load)
        """
        if "jpegtran" in self.tools:
            return u"jpegtran -copy none -progressive -optimize -outfile '%(file)s' '%(file)s'"
        elif "jpegoptim" in self.tools:
            return u"jpegoptim -f --strip-all '%(file)s'"
        return None

    def png_cli(self):
        _cmds = []
        if "optipng" in self.tools:
            _cmds.append(u"optipng -force -o7 '%(file)s'")
        if "advpng" in self.tools:
            _cmds.append(u"advpng -z4 '%(file)s'")
        if "pngcrush" in self.tools:
            _cmds.extend(
                (u"pngcrush -rem gAMA -rem alla -rem cHRM -rem iCCP -rem sRGB -rem time '%(file)s' '%(file)s.tmp'",
                 u"mv '%(file)s.tmp' '%(file)s'")
            )
        return " && ".join(_cmds)
