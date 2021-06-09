# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import Optional
import logging

# Dependency Imports
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
import discord

# Music Imports
from ...utils import BOT_SONG_RE
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Music.cog.Commands.lyrics")


class LyricsCommands(MixinMeta, ABC, metaclass=CompositeMetaClass):
    @commands.group(name="lyrics")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_lyrics(self, ctx: commands.Context):
        """Get for a songs lyrics."""

    @command_lyrics.command(name="search")
    async def command_lyrics_search(self, ctx, *, artistsong: str):
        """
        Returns Lyrics for Song Lookup.
        User arguments - artist/song
        """
        async with ctx.typing():
            title, artist, lyrics, source = await self.get_lyrics_string(artistsong)
            title = "" if title == "" else f"{title} by {artist}"
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content, start=1):
                embed = discord.Embed(
                    title=f"{title}",
                    description=page,
                    colour=await self.bot.get_embed_color(ctx.channel),
                )
                if source:
                    embed.set_footer(
                        text=f"Requested by {ctx.message.author} | Source: {source} | Page: {index}/{len(paged_content)}"
                    )
                paged_embeds.append(embed)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)

    @command_lyrics.command(name="spotify")
    async def command_lyrics_spotify(self, ctx, user: Optional[discord.Member] = None):
        """
        Returns Lyrics from Discord Member song.
        Optional User arguments - Mention/ID, no argument returns your own
        """
        if user is None:
            user = ctx.author
        spot = next(
            (activity for activity in user.activities if isinstance(activity, discord.Spotify)),
            None,
        )
        if spot is None:
            return await self.send_embed_msg(
                ctx, title=f"I'm unable to tell what {user.name} is listening to"
            )
        embed = discord.Embed(
            title=f"{user.name}'s Spotify",
            colour=await self.bot.get_embed_color(ctx.channel),
        )
        embed.add_field(name="Song", value=spot.title)
        embed.add_field(name="Artist", value=spot.artist)
        embed.add_field(name="Album", value=spot.album)
        embed.add_field(
            name="Track Link",
            value=f"[{spot.title}](https://open.spotify.com/track/{spot.track_id})",
        )
        embed.set_thumbnail(url=spot.album_cover_url)
        await self.send_embed_msg(ctx, embed=embed)

        async with ctx.typing():
            title, artist, lyrics, source = await self.get_lyrics_string(
                f"{spot.artist} {spot.title}"
            )
            title = "" if title == "" else f"{title} by {artist}"
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content, start=1):
                embed = discord.Embed(
                    title=f"{title}",
                    description=page,
                    colour=await self.bot.get_embed_color(ctx.channel),
                )
                if source:
                    embed.set_footer(
                        text=f"Requested by {ctx.message.author} | Source: {source} | Page: {index}/{len(paged_content)}"
                    )
                paged_embeds.append(embed)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)

    @command_lyrics.command(name="playing")
    async def command_lyrics_playing(self, ctx):
        """
        Returns Lyrics for bot's current track.
        """
        cached = await self.config_cache.currently_playing_name.get_context_value(ctx.guild)
        if not cached:
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        botsong = BOT_SONG_RE.sub("", cached).strip()
        async with ctx.typing():
            title, artist, lyrics, source = await self.get_lyrics_string(botsong)
            title = "" if title == "" else f"{title} by {artist}"
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content, start=1):
                embed = discord.Embed(
                    title="{}".format(title),
                    description=page,
                    colour=await self.bot.get_embed_color(ctx.channel),
                )
                if source:
                    embed.set_footer(
                        text=f"Requested by {ctx.message.author} | Source: {source} | Page: {index}/{len(paged_content)}"
                    )
                paged_embeds.append(embed)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)
