from ...core import CompositeMetaClass
from .commands import HeadlessCommands


class Buttons(
    HeadlessCommands,
    metaclass=CompositeMetaClass,
):
    """Class joining all button subclasses"""
