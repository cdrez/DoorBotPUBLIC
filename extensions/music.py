#!/usr/bin/python3

from asyncio.tasks import ensure_future
import datetime, uuid
import string
import asyncio, random, requests
from disnake.interactions.application_command import ApplicationCommandInteraction
from async_timeout import timeout
import sys, traceback, itertools
from functools import partial
from yt_dlp import YoutubeDL
import disnake
from disnake.ext import commands
from utils.funcs import Funcs

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # ipv6 addresses cause issues sometimes
    'usenetrc': True
    }


ffmpegopts = {
    'before_options': '-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 10M',
    'options': '-vn -b:a 128k'
}

ytdl = YoutubeDL(ytdlopts)

author_id = 210170891433148416

print("YO")

class VoiceConnectionError(commands.CommandError):
    """Custom Exception Class for connection errors."""

class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels"""

class YTDLSource(disnake.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')
        if "duration" in data:
                self.time = str(datetime.timedelta(seconds=data.get('duration')))

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, inter: ApplicationCommandInteraction, search: str, *, loop, download=False):
        """Creates an audio player source.
        This may take longer than 3 seconds, so it is being defered at the start.
        """
        await inter.response.defer()
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        if "duration" in data:
                resp = f'```ini\n[Added {data["title"]} - ({str(datetime.timedelta(seconds=data["duration"]))}) to the Queue.]\n```'
                await inter.edit_original_message(content = resp)
        else:
            resp = f'```ini\n[Added {data["title"]} to the Queue.]\n```'
            await inter.edit_original_message(content = resp)

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': inter.author, 'title': data['title']}

        return cls(disnake.FFmpegPCMAudio(source, **ffmpegopts), data=data, requester=inter.author)

    @classmethod
    async def create_playlist_source(cls, inter: ApplicationCommandInteraction, playlist, shuffle, loop):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=playlist, download=False)
        data = await loop.run_in_executor(None, to_run)

        userplaylist = []
        if 'entries' in data:
            # Place all songs in playlist on new list/dict
            data = data['entries']
            for entry in data:
                # has to be in this order for the queue system
                userplaylist.append({'webpage_url': entry['webpage_url'], 'requester': inter.author, 'title': entry['title']})

            if shuffle is True:
                random.shuffle(userplaylist)

            await inter.response.send_message(f'```ini\n[Added Playlist to the Queue.]\n```')
            return userplaylist
        else:
            return None


    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']
        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(disnake.FFmpegPCMAudio(data['url'], **ffmpegopts), data=data, requester=requester)


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, inter: ApplicationCommandInteraction):
        self.bot = inter.bot
        self._guild = inter.guild
        funcs = Funcs(self.bot)

        self._channel = disnake.utils.get(inter.guild.text_channels, name='bot-spam')
        if self._channel is None:
            self._channel = disnake.utils.get(inter.guild.text_channels, name='bot-channel')
            if self._channel is None:
                self._channel = inter.channel
        # self._cog = ctx.cogs

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self._cog = inter.bot.get_cog('Music')

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        inter.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return await self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            if hasattr(source, 'time'):
                self.np = await self._channel.send(f'**Now Playing:** `{source.title}` ({source.time}) requested by '
                                               f'`{source.requester}`')
            else:
                self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except disnake.HTTPException:
                pass


    async def destroy(self, guild):
        """Disconnect and cleanup the player."""
        # return self.bot.loop.create_task(self._cog.cleanup(guild))
        # return await guild.voice_client.disconnect(force=True)
        return self.bot.loop.create_task(self._cog.cleanup(guild))

class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect(force=True)
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except disnake.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, inter: ApplicationCommandInteraction):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[inter.guild_id]
        except KeyError:
            player = MusicPlayer(inter)
            self.players[inter.guild_id] = player

        return player

    @commands.slash_command()
    async def connect(self, inter: ApplicationCommandInteraction, channel: disnake.VoiceChannel=None):
        """Connect to voice channel."""
        if not await self.ensure_role(inter):
            return await funcs.permission_error(inter)
        if not channel:
            try:
                channel = inter.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel('No channel to join. Please either specify a valid channel or join one.')

        vc = inter.guild.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect(reconnect=False)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

        await inter.response.send_message(f'Connected to: **{channel}**')

    @commands.slash_command()
    async def tts(self, inter: ApplicationCommandInteraction, text:str):
        """Brian Text To Speech"""
        if not await self.ensure_role(inter):
            return await funcs.permission_error(inter)

        await self.ensure_voice(inter)

        data = {'voice': 'Brian', 'text': text}
        r = requests.post('https://streamlabs.com/polly/speak', data=data)
        r = r.json()
        r = r['speak_url']

        player = self.get_player(inter)

        source = await YTDLSource.create_source(inter, r, loop=self.bot.loop, download=False)

        await player.queue.put(source)

    @commands.slash_command()
    async def ftts(self, inter: ApplicationCommandInteraction, text:str):

        if not await self.ensure_role(inter):
            return await funcs.permission_error(inter)

        await self.ensure_voice(inter)

        data = {'voice': 'Mathieu', 'text': text}
        r = requests.post('https://streamlabs.com/polly/speak', data=data)
        r = r.json()
        r = r['speak_url']

        player = self.get_player(inter)

        source = await YTDLSource.create_source(inter, r, loop=self.bot.loop, download=False)

        await player.queue.put(source)

    @commands.slash_command()
    async def stts(self, inter: ApplicationCommandInteraction, text:str = None, voice:str = None):
        if not await self.ensure_role(inter):
            return await funcs.permission_error(inter)

        if voice is None:
            embed=disnake.Embed(title="Voices")
            embed.add_field(name='Unsorted', value='Vitoria Ricardo Chantal Enrique Conchita Naja Mads Ruben Lotte Russell Nicole Emma Brian Amy Raveena Joanna Salli Kimberly Kendra Justin Joey Ivy Geraint Mathieu Celine Marlene Hans Karl Dora Giorgio Carla Mizuki Liv Maja Jan Ewa Jacek Ines Cristiano Carmen Maxim Tatyana Astrid Filiz Penelope Miguel Gwyneth Albanian', inline=False)
            return await inter.response.send_message(embed=embed)

        await self.ensure_voice(inter)

        voice = voice.capitalize()

        data = {'voice': voice, 'text': text}
        try:
            r = requests.post('https://streamlabs.com/polly/speak', data=data)
            r = r.json()
            r = r['speak_url']

            player = self.get_player(inter)

            source = await YTDLSource.create_source(inter, r, loop=self.bot.loop, download=False)

            await player.queue.put(source)
        except:
            await inter.response.send_message('Voice not found. For list just type "a!stts"')

    @commands.slash_command()
    async def play(self, inter: ApplicationCommandInteraction, search: str):
        """Request a song and add it to the queue."""
        if not await self.ensure_role(inter):
            return await funcs.permission_error(inter)

        await self.ensure_voice(inter)

        player = self.get_player(inter)

        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        source = await YTDLSource.create_source(inter, search, loop=self.bot.loop, download=False)

        await player.queue.put(source)


    @commands.slash_command()
    async def playlist(self, inter: ApplicationCommandInteraction, playlist, shuffle=None):
        """Play a YouTube playlist."""
        if not await self.ensure_role(inter):
            return await funcs.permission_error(inter)

        if shuffle is not None:
            shuffle = True


        await self.ensure_voice(inter)

        player = self.get_player(inter)

        source = await YTDLSource.create_playlist_source(inter, playlist, shuffle, loop=self.bot.loop)

        if source is None:
            await inter.response.send_message("Your playlist could not be found.")
        else:
            for song in source:
                # Places each song in the queue
                await player.queue.put(song)


    @commands.slash_command()
    async def pause(self, inter: ApplicationCommandInteraction):
        """Pause the currently playing song."""
        if not await self.ensure_role(inter):
            return await funcs.permission_error(inter)

        vc = inter.guild.voice_client

        if not vc or not vc.is_playing():
            return await inter.response.send_message('I am not currently playing anything!')
        elif vc.is_paused():
            return

        vc.pause()
        await inter.response.send_message(f'**`{inter.author}`**: Paused the song!')

    @commands.slash_command()
    async def resume(self, inter: ApplicationCommandInteraction):
        """Resume the currently paused song."""
        if not await self.ensure_role(inter):
            funcs.permission_error(inter)
        vc = inter.guild.voice_client

        if not vc or not vc.is_connected():
            return await inter.send('I am not currently playing anything!')
        elif not vc.is_paused():
            return

        vc.resume()
        await inter.response.send_message(f'**`{inter.author}`**: Resumed the song!')

    @commands.slash_command()
    async def skip(self, inter: ApplicationCommandInteraction):
        """Skip the song."""
        if not await self.ensure_role(inter):
            funcs.permission_error(inter)
        vc = inter.guild.voice_client

        if not vc or not vc.is_connected():
            return await inter.response.send_message('I am not currently playing anything!')

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await inter.response.send_message(f'**`{inter.author}`**: Skipped the song!')

    @commands.slash_command()
    async def queue(self, inter: ApplicationCommandInteraction):
        """Retrieve a basic queue of upcoming songs."""
        vc = inter.guild.voice_client

        if not vc or not vc.is_connected():
            return await inter.response.send_message('I am not currently connected to voice!')

        player = self.get_player(inter)
        if player.queue.empty():
            return await inter.response.send_message('There are currently no more queued songs.')

        # Grab up to 5 entries from the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = disnake.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

        await inter.response.send_message(embed=embed)

    @commands.slash_command()
    async def playing(self, inter: ApplicationCommandInteraction):
        """Display information about the currently playing song."""
        vc = inter.guild.voice_client

        if not vc or not vc.is_connected():
            return await inter.response.send_message('I am not currently connected to voice!')

        player = self.get_player(inter)
        if not player.current:
            return await inter.response.send_message('I am not currently playing anything!')

        try:
            # Remove our previous now_playing message.
            await player.np.delete()
        except disnake.HTTPException:
            pass

        player.np = await inter.response.send_message(f'**Now Playing:** `{vc.source.title}` '
                                   f'requested by `{vc.source.requester}`')

    @commands.slash_command()
    async def volume(self, inter: ApplicationCommandInteraction, *, volume: float):
        """Change the player volume."""
        if await self.ensure_role(inter):
            vc = inter.guild.voice_client

            if not vc or not vc.is_connected():
                return await inter.response.send_message('I am not currently connected to voice!')

            if not 0 < volume < 101:
                return await inter.response.send_message('Please enter a value between 1 and 100.')

            player = self.get_player(inter)

            if vc.source:
                vc.source.volume = volume / 100

            player.volume = volume / 100
            await inter.response.send_message(f'**`{inter.author}`**: Set the volume to **{volume}%**')



    # """This may not work"""
    # @commands.slash_command()
    # async def remove(self, inter: ApplicationCommandInteraction, num: int):
    #     player = self.get_player(inter)
    #     if player.queue.empty():
    #         return await inter.response.send_message('There are currently no more queued songs.')

    #     inter.response.send_message("Type /remove [#] to remove that song\n")
    #     upcoming = list(itertools.islice(player.queue._queue, 0, 5))

    #     i = 0
    #     queue = []
    #     for song in upcoming:
    #         i += 1
    #         queue.append(i + f'**`{song["title"]}`**')
    #     fmt = '\n'.join(queue)
    #     embed = disnake.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

    #     await inter.response.send_message.send(embed=embed)




    @commands.slash_command()
    async def stop(self, inter: ApplicationCommandInteraction):
        """Stop the currently playing song and destroy the player."""

        if await self.ensure_role(inter):
            vc = inter.guild.voice_client

            if not vc or not vc.is_connected():
                await inter.response.send_message('I am not currently playing anything!')

            await self.cleanup(inter.guild)

            await inter.response.send_message('Bot stopped.')

    async def ensure_voice(self, inter: ApplicationCommandInteraction):
        if not inter.guild.voice_client:
            if inter.author.voice:
                await inter.author.voice.channel.connect()
            else:
                await inter.response.send_message("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        # elif inter.guild.voice_client.is_playing():
        #     inter.guild.voice_client.stop()

    async def ensure_role(self, inter: ApplicationCommandInteraction):
        dj = disnake.utils.get(inter.guild.roles, name="DJ")
        if(dj is None):
            print("dj is none")
        if dj in inter.author.roles or dj is None or inter.author.guild_permissions.administrator or inter.author.id == author_id:
            return True


def setup(bot):
    bot.add_cog(Music(bot))
