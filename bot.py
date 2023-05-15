#!/usr/bin/python3

import os, sys
import logging
import disnake
from disnake.ext import commands

logger = logging.getLogger('disnake')
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = disnake.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='a!', intents=intents)

bot.remove_command('help')


BOT_TOKEN = os.getenv('BOT_TOKEN')


path = os.path.dirname(sys.argv[0])
for filename in os.listdir('extensions'):
    print(filename)
    if filename.endswith('.py'):
        bot.load_extension(f'extensions.{filename[:-3]}')

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('-------')

    await bot.change_presence(activity=disnake.Activity(type=disnake.ActivityType.playing, name="with slash commands"))

try:
    bot.run(BOT_TOKEN)
except KeyboardInterrupt:
    exit
