import asyncio
import logging
import time
from pathlib import Path

from typing import Dict

import discord
import lavalink

from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

from ...audio_logging import debug_exc_log
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Tasks.player")
_ = Translator("Audio", Path(__file__))


class PlayerTasks(MixinMeta, metaclass=CompositeMetaClass):
    async def player_automated_timer(self) -> None:
        stop_times: Dict = {}
        pause_times: Dict = {}
        while True:
            async for p in AsyncIter(lavalink.all_players()):
                server = p.guild
                if await self.bot.cog_disabled_in_guild(self, server):
                    continue

                if [self.bot.user] == p.channel.members:
                    stop_times.setdefault(server.id, time.time())
                    pause_times.setdefault(server.id, time.time())
                else:
                    stop_times.pop(server.id, None)
                    if p.paused and server.id in pause_times:
                        try:
                            await p.pause(False)
                        except Exception as err:
                            debug_exc_log(log, err, "Exception raised in Audio's unpausing %r.", p)
                    pause_times.pop(server.id, None)
            servers = stop_times.copy()
            servers.update(pause_times)
            async for sid in AsyncIter(servers, steps=5):
                server_obj = self.bot.get_guild(sid)
                if not server_obj:
                    stop_times.pop(sid, None)
                    pause_times.pop(sid, None)
                    try:
                        player = lavalink.get_player(sid)
                        await self.api_interface.persistent_queue_api.drop(sid)
                        player.store("autoplay_notified", False)
                        await player.stop()
                        await player.disconnect()
                        await self.config_cache.autoplay.set_currently_in_guild(server_obj)
                    except Exception as err:
                        debug_exc_log(
                            log, err, "Exception raised in Audio's emptydc_timer for %s.", sid
                        )

                elif sid in stop_times and await self.config_cache.empty_dc.get_context_value(
                    server_obj
                ):
                    emptydc_timer = await self.config_cache.empty_dc_timer.get_context_value(
                        server_obj
                    )
                    if (time.time() - stop_times[sid]) >= emptydc_timer:
                        stop_times.pop(sid)
                        try:
                            player = lavalink.get_player(sid)
                            await self.api_interface.persistent_queue_api.drop(sid)
                            player.store("autoplay_notified", False)
                            await player.stop()
                            await player.disconnect()
                            await self.config_cache.autoplay.set_currently_in_guild(server_obj)
                        except Exception as err:
                            if "No such player for that guild" in str(err):
                                stop_times.pop(sid, None)
                            debug_exc_log(
                                log, err, "Exception raised in Audio's emptydc_timer for %s.", sid
                            )
                elif sid in pause_times and await self.config_cache.empty_pause.get_context_value(
                    server_obj
                ):
                    emptypause_timer = await self.config_cache.empty_pause_timer.get_context_value(
                        server_obj
                    )
                    if (time.time() - pause_times.get(sid, 0)) >= emptypause_timer:
                        try:
                            await lavalink.get_player(sid).pause()
                        except Exception as err:
                            if "No such player for that guild" in str(err):
                                pause_times.pop(sid, None)
                            debug_exc_log(
                                log, err, "Exception raised in Audio's pausing for %s.", sid
                            )
            await asyncio.sleep(5)