# -*- coding: utf-8 -*-
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("chaostoolkit-opentracing")
except PackageNotFoundError:
    __version__ = "unknown"
