# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass


class LyricUtilities(MixinMeta, ABC, metaclass=CompositeMetaClass):
    """Base class to hold all Lyric utility methods"""
