from youtube_dl import YoutubeDL
import yt_dlp

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # ipv6 addresses cause issues sometimes
    'usenetrc': True
    }

with yt_dlp.YoutubeDL(ytdlopts) as ydl:
    ydl.download(['https://www.youtube.com/watch?v=UTH1VNHLjng'])
    #'postprocessors': [{
    #    'key': 'FFmpegExtractAudio',
    #    'preferredcodec': 'mp3',
    #    'preferredquality': '192',
    #}],

