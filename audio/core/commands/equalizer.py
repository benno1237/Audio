# Future Imports
from __future__ import annotations

# Standard Library Imports
import asyncio
import contextlib
import logging
import re

# Dependency Imports
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, humanize_number, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu, start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
import discord

# My Modded Imports
import lavalink

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Music.cog.Commands.equalizer")


class EqualizerCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="eq", invoke_without_command=True)
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_equalizer(self, ctx: commands.Context):
        """Equalizer management.

        Band positions are 1-15 and values have a range of -0.25 to 1.0.
        Band names are 25, 40, 63, 100, 160, 250, 400, 630, 1k, 1.6k, 2.5k, 4k,
        6.3k, 10k, and 16k Hz.
        Setting a band value to -0.25 nullifies it while +0.25 is double.
        """
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        player = lavalink.get_player(ctx.guild.id)
        reactions = [
            "\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
            "\N{BLACK UP-POINTING DOUBLE TRIANGLE}",
            "\N{UP-POINTING SMALL RED TRIANGLE}",
            "\N{DOWN-POINTING SMALL RED TRIANGLE}",
            "\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}",
            "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}",
            "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            "\N{BLACK CIRCLE FOR RECORD}\N{VARIATION SELECTOR-16}",
            "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}",
        ]
        await self._eq_msg_clear(player.fetch("eq_message"))
        eq_message = await self.send_embed_msg(
            ctx=ctx,
            description=box(player.equalizer.visualise(), lang="ini"),
            no_embed=True,
        )

        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            with contextlib.suppress(discord.HTTPException):
                await eq_message.add_reaction("\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}")
        else:
            start_adding_reactions(eq_message, reactions)

        player.store("eq_message", eq_message)
        await self._eq_interact(ctx, player, eq_message, 0, player.equalizer)

    @command_equalizer.command(name="delete", aliases=["del", "remove"])
    async def command_equalizer_delete(self, ctx: commands.Context, eq_preset: str):
        """Delete a saved eq preset."""
        async with self.config.custom("EQUALIZER", ctx.guild.id).eq_presets() as eq_presets:
            eq_preset = eq_preset.lower()
            try:
                if eq_presets[eq_preset][
                    "author"
                ] != ctx.author.id and not await self._can_instaskip(ctx, ctx.author):
                    return await self.send_embed_msg(
                        ctx,
                        title="Unable To Delete Preset",
                        description="You are not the author of that preset setting.",
                    )
                del eq_presets[eq_preset]
            except KeyError:
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Delete Preset",
                    description=(
                        "{eq_preset} is not in the eq preset list.".format(
                            eq_preset=eq_preset.capitalize()
                        )
                    ),
                )
            except TypeError:
                if await self._can_instaskip(ctx, ctx.author):
                    del eq_presets[eq_preset]
                else:
                    return await self.send_embed_msg(
                        ctx,
                        title="Unable To Delete Preset",
                        description="You are not the author of that preset setting.",
                    )

        await self.send_embed_msg(
            ctx, title=("The {preset_name} preset was deleted.".format(preset_name=eq_preset))
        )

    @command_equalizer.command(name="list")
    async def command_equalizer_list(self, ctx: commands.Context):
        """List saved eq presets."""
        eq_presets = await self.config.custom("EQUALIZER", ctx.guild.id).eq_presets()
        if not eq_presets.keys():
            return await self.send_embed_msg(ctx, title="No saved equalizer presets.")

        space = "\N{EN SPACE}"
        header_name = "Preset Name"
        header_author = "Author"
        header = box(
            "[{header_name}]{space}[{header_author}]\n".format(
                header_name=header_name, space=space * 9, header_author=header_author
            ),
            lang="ini",
        )
        preset_list = ""
        for preset, data in eq_presets.items():
            try:
                author = self.bot.get_user(data["author"])
            except TypeError:
                author = "None"
            msg = f"{preset}{space * (22 - len(preset))}{author}\n"
            preset_list += msg

        page_list = []
        colour = await ctx.embed_colour()
        for page in pagify(preset_list, delims=[", "], page_length=1000):
            formatted_page = box(page, lang="ini")
            embed = discord.Embed(colour=colour, description=f"{header}\n{formatted_page}")
            embed.set_footer(
                text="{num} preset(s)".format(num=humanize_number(len(list(eq_presets.keys()))))
            )
            page_list.append(embed)
        await menu(ctx, page_list, DEFAULT_CONTROLS)

    @command_equalizer.command(name="load")
    async def command_equalizer_load(self, ctx: commands.Context, eq_preset: str):
        """Load a saved eq preset."""
        eq_preset = eq_preset.lower()
        eq_presets = await self.config.custom("EQUALIZER", ctx.guild.id).eq_presets()
        try:
            eq_values = eq_presets[eq_preset]["bands"]
        except KeyError:
            return await self.send_embed_msg(
                ctx,
                title="No Preset Found",
                description=(
                    "Preset named {eq_preset} does not exist.".format(eq_preset=eq_preset)
                ),
            )
        except TypeError:
            eq_values = eq_presets[eq_preset]

        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")

        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        player = lavalink.get_player(ctx.guild.id)
        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Load Preset",
                description="You need the DJ role to load equalizer presets.",
            )
        player.store("notify_channel", ctx.channel.id)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = eq_values
            eq_data["name"] = eq_preset
        await self._eq_check(ctx, player)
        await self._eq_msg_clear(player.fetch("eq_message"))
        message = await ctx.send(
            content=box(player.equalizer.visualise(), lang="ini"),
            embed=discord.Embed(
                colour=await ctx.embed_colour(),
                title=("The {eq_preset} preset was loaded.".format(eq_preset=eq_preset)),
            ),
        )
        player.store("eq_message", message)

    @command_equalizer.command(name="reset")
    async def command_equalizer_reset(self, ctx: commands.Context):
        """Reset the eq to 0 across all bands."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Modify Preset",
                description="You need the DJ role to reset the equalizer.",
            )
        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        player.equalizer.reset()
        await player.set_equalizer(player.equalizer)
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        await self._eq_msg_clear(player.fetch("eq_message"))
        message = await self.send_embed_msg(
            ctx=ctx,
            title="Equalizer values have been reset.",
            description=box(player.equalizer.visualise(), lang="ini"),
            no_embed=True,
        )
        player.store("eq_message", message)

    @command_equalizer.command(name="save")
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def command_equalizer_save(self, ctx: commands.Context, eq_preset: str = None):
        """Save the current eq settings to a preset."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Save Preset",
                description="You need the DJ role to save equalizer presets.",
            )
        if not eq_preset:
            await self.send_embed_msg(ctx, title="Please enter a name for this equalizer preset.")
            try:
                eq_name_msg = await self.bot.wait_for(
                    "message",
                    timeout=15.0,
                    check=MessagePredicate.regex(fr"^(?!{re.escape(ctx.prefix)})", ctx),
                )
                eq_preset = eq_name_msg.content.split(" ")[0].strip('"').lower()
            except asyncio.TimeoutError:
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Save Preset",
                    description="No equalizer preset name entered, try the command again later.",
                )
        eq_preset = eq_preset or ""
        eq_exists_msg = None
        eq_preset = eq_preset.lower().lstrip(ctx.prefix)
        eq_presets = await self.config.custom("EQUALIZER", ctx.guild.id).eq_presets()
        eq_list = list(eq_presets.keys())

        if len(eq_preset) > 20:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Save Preset",
                description="Try the command again with a shorter name.",
            )
        if eq_preset in eq_list:
            eq_exists_msg = await self.send_embed_msg(
                ctx, title="Preset name already exists, do you want to replace it?"
            )
            start_adding_reactions(eq_exists_msg, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(eq_exists_msg, ctx.author)
            await self.bot.wait_for("reaction_add", check=pred)
            if not pred.result:
                await self._clear_react(eq_exists_msg)
                embed2 = discord.Embed(colour=await ctx.embed_colour(), title="Not saving preset.")
                ctx.command.reset_cooldown(ctx)
                return await eq_exists_msg.edit(embed=embed2)

        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        to_append = {eq_preset: {"author": ctx.author.id, "bands": player.equalizer.get()}}
        new_eq_presets = {**eq_presets, **to_append}
        await self.config.custom("EQUALIZER", ctx.guild.id).eq_presets.set(new_eq_presets)
        embed3 = discord.Embed(
            colour=await ctx.embed_colour(),
            title="Current equalizer saved to the {preset_name} preset.".format(
                preset_name=eq_preset
            ),
        )
        if eq_exists_msg:
            await self._clear_react(eq_exists_msg)
            await eq_exists_msg.edit(embed=embed3)
        else:
            await self.send_embed_msg(ctx, embed=embed3)

    @command_equalizer.command(name="set")
    async def command_equalizer_set(
        self, ctx: commands.Context, band_name_or_position, band_value: float
    ):
        """Set an eq band with a band number or name and value.

        Band positions are 1-15 and values have a range of -0.25 to 1.0.
        Band names are 25, 40, 63, 100, 160, 250, 400, 630, 1k, 1.6k, 2.5k, 4k,
        6.3k, 10k, and 16k Hz.
        Setting a band value to -0.25 nullifies it while +0.25 is double.
        """
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")

        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Set Preset",
                description="You need the DJ role to set equalizer presets.",
            )

        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        band_names = [
            "25",
            "40",
            "63",
            "100",
            "160",
            "250",
            "400",
            "630",
            "1k",
            "1.6k",
            "2.5k",
            "4k",
            "6.3k",
            "10k",
            "16k",
        ]

        if band_value > 1:
            band_value = 1
        elif band_value <= -0.25:
            band_value = -0.25
        else:
            band_value = round(band_value, 1)

        try:
            band_number = int(band_name_or_position) - 1
        except ValueError:
            band_number = 1000

        if (
            band_number not in range(player.equalizer.band_count)
            and band_name_or_position not in band_names
        ):
            return await self.send_embed_msg(
                ctx,
                title="Invalid Band",
                description=(
                    "Valid band numbers are 1-15 or the band names listed in "
                    "the help for this command."
                ),
            )

        if band_name_or_position in band_names:
            band_pos = band_names.index(band_name_or_position)
            band_int = False
            player.equalizer.set_gain(int(band_pos), band_value)
            await player.set_equalizer(equalizer=player.equalizer)
        else:
            band_int = True
            player.equalizer.set_gain(band_number, band_value)
            await player.set_equalizer(equalizer=player.equalizer)

        await self._eq_msg_clear(player.fetch("eq_message"))
        async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
            eq_data["eq_bands"] = player.equalizer.get()
            eq_data["name"] = player.equalizer.name
        band_name = band_names[band_number] if band_int else band_name_or_position
        message = self.send_embed_msg(
            ctx=ctx,
            title="Preset Modified\nThe {band_name}Hz band has been set to {band_value}".format(
                band_name=band_name, band_value=band_value
            ),
            description=box(player.equalizer.visualise(), lang="ini"),
            no_embed=True,
        )
        player.store("eq_message", message)
