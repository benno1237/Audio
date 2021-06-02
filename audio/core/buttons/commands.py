from pathlib import Path

import discord
import lavalink
from lavalink.filters import Volume
from redbot.core.i18n import Translator

from ...core import CompositeMetaClass
from ...core.abc import MixinMeta

_ = Translator("Audio", Path(__file__))


class HeadlessCommands(MixinMeta, metaclass=CompositeMetaClass):
    async def button_volume_command(self, interaction: discord.Interaction, vol: float = None):
        guild = interaction.guild
        player = lavalink.get_player(guild.id)
        max_volume, max_source = await self.config_cache.volume.get_max_and_source(
            guild, player.channel
        )
        if vol:
            volume = min(
                max(vol, 0),
                max_volume,
            )
        else:
            volume = None

        if volume:
            vol = Volume(value=volume)
            if player.volume != vol:
                await player.set_volume(vol)
            description = (
                "Currently set to **{volume}%**\n\n"
                "Maximum allowed volume here is **{max_volume}%** "
                "due to {restrictor} restrictions."
            ).format(volume=int(volume * 100), max_volume=max_volume, restrictor=max_source)

        else:
            volume = player.volume.value
            description = (
                "Currently set to **{volume}%**\n\n"
                "Maximum allowed volume here is **{max_volume}%** "
                "due to {restrictor} restrictions."
            ).format(volume=int(volume * 100), max_volume=max_volume, restrictor=max_source)

        embed = discord.Embed(
            title=_("Volume"),
            description=description,
        )
        await self.send_interaction_msg(interaction, embed=embed)

    async def button_queue_shuffle_command(
        self, interaction: discord.Interaction, player: lavalink.Player
    ):
        """Shuffles the queue."""
        player.force_shuffle(0)
        return await self.send_interaction_msg(
            interaction=interaction, title=_("Queue has been shuffled."), ephemeral=False
        )

    async def button_pause_command(
        self, interaction: discord.Interaction, player: lavalink.Player
    ):
        """Pause playback."""
        await player.pause(True)
        return await self.send_interaction_msg(
            interaction=interaction, title=_("Player Paused."), ephemeral=False
        )

    async def button_resume_command(
        self, interaction: discord.Interaction, player: lavalink.Player
    ):
        """Resume playback."""
        await player.pause(False)
        return await self.send_interaction_msg(
            interaction=interaction, title=_("Player Resumed."), ephemeral=False
        )
