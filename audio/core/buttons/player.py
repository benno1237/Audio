from pathlib import Path
from typing import Optional

import discord
import lavalink
from discord.ext.commands import Context
from redbot.core.i18n import Translator

from ...core.abc import MixinMeta
from ..utilities import SettingCacheManager

_ = Translator("Audio", Path(__file__))


class PlayerView(discord.ui.View):
    def __init__(
        self, cog: MixinMeta, ctx: Context, config_cache: SettingCacheManager, *args, **kwargs
    ):
        super(PlayerView, self).__init__(*args, **kwargs)
        self.cog = cog
        self.ctx = ctx
        self.config_cache = config_cache
        self.player: lavalink.Player = None
        self.bot_vc: discord.VoiceChannel = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user:
            return False
        dj_mode = await self.config_cache.dj_status.get_context_value(interaction.guild)
        vote_mode = await self.config_cache.votes.get_context_value(interaction.guild)
        is_privileged = await self.cog._can_instaskip(self.ctx, interaction.user)
        is_alone = await self.cog.is_requester_alone(self.ctx)
        if not is_privileged and not is_alone:
            if dj_mode or vote_mode:
                if dj_mode:
                    await interaction.response.send_message(
                        content="You need to be a DJ to control this player.", ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        content="Player controls are disabled when vote mode is enabled.",
                        ephemeral=True,
                    )
                return False

        if (player := self.get_player(interaction)) is None:
            self.stop()
            return False
        self.player = player
        if not self.in_vc(interaction.user) and not is_privileged:
            await interaction.response.send_message(
                content=f"You cannot interact with this player, you must first join {self.bot_vc.mention} before you can interact with it.",
                ephemeral=True,
            )
            return False
        return True

    def in_vc(self, user: discord.Member) -> bool:
        user_vc = self.cog.rgetattr(user, "voice.channel", None)
        botr_vc = self.bot_vc = self.cog.rgetattr(user, "guild.me.voice.channel", None)
        return user_vc and botr_vc and user_vc == botr_vc

    def get_player(self, interaction: discord.Interaction) -> Optional[lavalink.Player]:
        try:
            return lavalink.get_player(interaction.guild.id)
        except (KeyError, IndexError, AttributeError):
            return

    @discord.ui.button(
        label="Play",
        style=discord.ButtonStyle.blurple,
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
        row=0,
    )
    async def play_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.player.is_playing:
            return await interaction.response.send_message(
                content="Player is already playing.", ephemeral=True
            )
        await self.cog.button_resume_command(interaction, self.player)

    @discord.ui.button(
        label="Pause",
        style=discord.ButtonStyle.grey,
        emoji="\N{DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}",
        row=0,
    )
    async def pause_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.player.paused:
            return await interaction.response.send_message(
                content="Player is already paused.", ephemeral=True
            )

        await self.cog.button_pause_command(interaction, self.player)

    @discord.ui.button(
        label="Stop",
        style=discord.ButtonStyle.red,
        emoji="\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}",
        row=0,
    )
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.ctx.invoke(self.cog.command_stop)

    @discord.ui.button(
        label="Previous",
        style=discord.ButtonStyle.blurple,
        emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
        row=1,
    )
    async def previous_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.ctx.invoke(self.cog.command_prev)

    @discord.ui.button(
        label="Next",
        style=discord.ButtonStyle.blurple,
        emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
        row=1,
    )
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.ctx.invoke(self.cog.command_skip)

    @discord.ui.button(
        label="Volume",
        style=discord.ButtonStyle.green,
        emoji="\N{SPEAKER WITH THREE SOUND WAVES}",
        row=4,
    )
    async def increase_volume_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        maximum, source = await self.config_cache.volume.get_max_and_source(
            guild=interaction.guild, channel=self.bot_vc
        )
        new_vol = self.player.volume.value + 0.05
        if new_vol > (maximum / 100):
            return await interaction.response.send_message(
                content="Player has reached it's maximum volume", ephemeral=True
            )
        await self.cog.button_volume_command(interaction=interaction, vol=new_vol)

    @discord.ui.button(
        label="Volume",
        style=discord.ButtonStyle.red,
        emoji="\N{SPEAKER WITH ONE SOUND WAVE}",
        row=4,
    )
    async def lower_volume_button(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        new_vol = self.player.volume.value - 0.05
        if 0 >= new_vol:
            return await interaction.response.send_message(
                content="Player has reached it's minimum volume", ephemeral=True
            )
        await self.cog.button_volume_command(interaction=interaction, vol=new_vol)

    @discord.ui.button(
        label="Shuffle",
        style=discord.ButtonStyle.grey,
        emoji="\N{TWISTED RIGHTWARDS ARROWS}",
        row=1,
    )
    async def shuffle_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not self.player.queue:
            return await interaction.response.send_message(
                content="There is no queue to shuffle, please enqueue some tracks first.",
                ephemeral=True,
            )
        await self.cog.button_queue_shuffle_command(interaction, self.player)
