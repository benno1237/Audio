import logging

from redbot.core import commands

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Utilities.BB8")


class BB8Utilities(MixinMeta, metaclass=CompositeMetaClass):
    def get_cross_emoji(self, ctx: commands.Context) -> str:
        if ctx.me.permissions_in(ctx.channel).external_emojis:
            cross = "<:crossedsabers:632685164408995870>"
        else:
            cross = "\N{CROSS MARK}"
        return cross
