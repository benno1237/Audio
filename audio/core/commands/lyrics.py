# Future Imports
from __future__ import annotations

import logging
# Standard Library Imports
from abc import ABC
from typing import MutableMapping, Optional

import discord
import lavalink
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass
from ..utilities.lyrics import BOT_SONG_RE, getlyrics

log = logging.getLogger("red.cogs.Music.cog.Commands.lyrics")


class LyricsCommands(MixinMeta, ABC, metaclass=CompositeMetaClass):

    def __init__(self):
        self._cache: MutableMapping = {}

    def cog_unload(self):
        self._cache = {}

    @commands.Cog.listener()
    async def on_red_audio_track_start(self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member):
        if not (guild and track):
            return
        if track.author.lower() not in track.title.lower():
            title = f"{track.title}"
        else:
            title = track.title
        self._cache[guild.id] = title
        auto_lyrics = await self.config.guild(guild).auto_lyrics()
        if auto_lyrics is True:
            notify_channel = lavalink.get_player(guild.id).fetch("channel")
            if not notify_channel:
                return
            notify_channel = self.bot.get_channel(notify_channel)
            botsong = BOT_SONG_RE.sub('', self._cache[guild.id]).strip()
            try:
                async with notify_channel.typing():
                    title, artist, lyrics, source = await getlyrics(botsong)
                    paged_embeds = []
                    paged_content = [p for p in pagify(lyrics, page_length=900)]
                    for index, page in enumerate(paged_content):
                        e = discord.Embed(title='{} by {}'.format(title, artist), description=page,
                                          colour=await self.bot.get_embed_color(notify_channel))
                        e.set_footer(
                            text='Requested by {} | Source: {} | Page: {}/{}'.format(track.requester, source, index,
                                                                                     len(paged_content)))
                        paged_embeds.append(e)
                await menu(notify_channel, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)
            except discord.Forbidden:
                return await notify_channel.send("Missing embed permissions..")

    @commands.Cog.listener()
    async def on_red_audio_queue_end(self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member):
        if not (guild and track):
            return
        if guild.id in self._cache:
            del self._cache[guild.id]

    @commands.command(name="autolyrics")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_autolyrics(self, ctx):
        """Toggle Lyrics to be shown when a new track starts"""
        auto_lyrics = await self.config.guild(ctx.guild).auto_lyrics()
        await self.config.guild(ctx.guild).auto_lyrics.set(not auto_lyrics)
        if not auto_lyrics:
            await ctx.send("Lyrics will be shown when a track starts.")
        else:
            await ctx.send("Lyrics will no longer be shown when a track starts.")

    @commands.command(name="search")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_search(self, ctx, *, artistsong: str):
        """
        Returns Lyrics for Song Lookup.
        User arguments - artist/song
        """
        async with ctx.typing():
            title, artist, lyrics, source = await getlyrics(artistsong)
            title = "" if title == "" else '{} by {}'.format(title, artist)
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content):
                e = discord.Embed(title='{}'.format(title), description=page,
                                  colour=await self.bot.get_embed_color(ctx.channel))
                e.set_footer(
                    text='Requested by {} | Source: {} | Page: {}/{}'.format(ctx.message.author, source, index,
                                                                             len(paged_content)))
                paged_embeds.append(e)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)

    @commands.command(name="spotify")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_spotify(self, ctx, user: Optional[discord.Member] = None):
        """
        Returns Lyrics from Discord Member song.
        Optional User arguments - Mention/ID, no argument returns your own

        NOTE: This command uses Discord presence intent, enable in development portal.

        """
        if user is None:
            user = ctx.author
        spot = next((activity for activity in user.activities if isinstance(activity, discord.Spotify)), None)
        if spot is None:
            await ctx.send("{} is not listening to Spotify".format(user.name))
            return
        embed = discord.Embed(title="{}'s Spotify".format(user.name),
                              colour=await self.bot.get_embed_color(ctx.channel))
        embed.add_field(name="Song", value=spot.title)
        embed.add_field(name="Artist", value=spot.artist)
        embed.add_field(name="Album", value=spot.album)
        embed.add_field(name="Track Link",
                        value="[{}](https://open.spotify.com/track/{})".format(spot.title, spot.track_id))
        embed.set_thumbnail(url=spot.album_cover_url)
        await ctx.send(embed=embed)

        async with ctx.typing():
            title, artist, lyrics, source = await getlyrics('{} {}'.format(spot.artist, spot.title))
            title = "" if title == "" else '{} by {}'.format(title, artist)
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content):
                e = discord.Embed(title='{}'.format(title), description=page,
                                  colour=await self.bot.get_embed_color(ctx.channel))
                e.set_footer(
                    text='Requested by {} | Source: {} | Page: {}/{}'.format(ctx.message.author, source, index,
                                                                             len(paged_content)))
                paged_embeds.append(e)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)

    @commands.command(name="playing")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_playing(self, ctx):
        """
        Returns Lyrics for bot's current track.
        """
        music = self.bot.get_cog('Music')
        if music is not None:
            try:
                botsong = BOT_SONG_RE.sub('', self._cache[ctx.guild.id]).strip()
            except AttributeError:
                return await ctx.send("Nothing playing.")
            except KeyError:
                return await ctx.send("Nothing playing.")
        else:
            return await ctx.send("Audio not loaded.")

        async with ctx.typing():
            title, artist, lyrics, source = await getlyrics(botsong)
            title = "" if title == "" else '{} by {}'.format(title, artist)
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content):
                e = discord.Embed(title='{}'.format(title), description=page,
                                  colour=await self.bot.get_embed_color(ctx.channel))
                e.set_footer(
                    text='Requested by {} | Source: {} | Page: {}/{}'.format(ctx.message.author, source, index,
                                                                             len(paged_content)))
                paged_embeds.append(e)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)
