import os, sys, asyncio, math, re, aiohttp, async_timeout, aiosocks, random, uuid
from io import BytesIO
import PIL, textwrap
from PIL import Image, ImageFont, ImageDraw
import disnake as discord

class Funcs():

    def __init__(self, bot):
        self.bot = bot
        self.mention_regex = re.compile('<@!?(?P<id>\\d+)>')
        self.session = aiohttp.ClientSession()
        self.image_mimes = ['image/png', 'image/pjpeg', 'image/jpeg', 'image/x-icon']

    async def permission_error(self, inter):
        await inter.response.send_message('You do not have permission for this command', ephemeral=True)
        return

    async def isimage(self, url: str):
        try:
            with async_timeout.timeout(5):
                async with self.session.head(url) as resp:
                    if resp.status == 200:
                        mime = resp.headers.get('Content-type', '').lower()
                        if any([mime == x for x in self.image_mimes]):
                            return True
                        else:
                            return False
        except:
            return False

    async def isgif(self, url: str):
        try:
            with async_timeout.timeout(5):
                async with self.session.head(url) as resp:
                    if resp.status == 200:
                        mime = resp.headers.get('Content-type', '').lower()
                        if mime == 'image/gif':
                            return True
                        else:
                            return False
        except:
            return False

    async def get_attachment_images(self, ctx, check_func):
        last_attachment = None
        img_urls = []
        async for m in ctx.channel.history(before=ctx.message, limit=25):
            check = False
            if m.content.startswith('http'):
                last_attachment = m.content
                check = await check_func(last_attachment)
            elif m.attachments:
                last_attachment = m.attachments[0].url
                check = await check_func(last_attachment)
            elif m.embeds:
                last_attachment = m.embeds[0].url
                check = await check_func(last_attachment)
            if check:
                img_urls.append(last_attachment)
                break
        return img_urls

    async def get_images_inter(self, inter, **kwargs):
        channel = inter.channel


    async def get_images(self, ctx, **kwargs):
        try:
            message = ctx.message
            channel = ctx.channel
            attachments = ctx.message.attachments
            mentions = ctx.message.mentions
            limit = kwargs.pop('limit', 8)
            urls = kwargs.pop('urls', [])
            gif = kwargs.pop('gif', False)
            msg = kwargs.pop('msg', True)
            if gif:
                check_func = self.isgif
            else:
                check_func = self.isimage
            if urls is None:
                urls = []
            elif type(urls) != tuple:
                urls = [urls]
            else:
                urls = list(urls)
            scale = kwargs.pop('scale', None)
            scale_msg = None
            int_scale = None
            if gif is False:
                for user in mentions:
                    if user.avatar:
                        urls.append(user.avatar_url_as(format='png', static_format='png'))
                    else:
                        urls.append(user.default_avatar_url)
                    limit += 1
            for attachment in attachments:
                urls.append(attachment.url)
            if scale:
                scale_limit = scale
                limit += 1
            if urls and (len(urls) > limit):
                await channel.send(':no_entry: `Max image limit (<= {0})`'.format(limit))
                ctx.command.reset_cooldown(ctx)
                return False
            img_urls = []
            count = 1
            for url in urls:
                user = None
                if url.startswith('<@'):
                    continue
                if (not url.startswith('http')):
                    url = 'http://' + url
                try:
                    if scale:
                        s_url = url[8:] if url.startswith('https://') else url[7:]
                        if str(math.floor(float(s_url))).isdigit():
                            int_scale = int(math.floor(float(s_url)))
                            scale_msg = '`Scale: {0}`\n'.format(int_scale)
                            if (int_scale > scale_limit) and (ctx.author.id != self.bot.owner.id):
                                int_scale = scale_limit
                                scale_msg = '`Scale: {0} (Limit: <= {1})`\n'.format(int_scale, scale_limit)
                            continue
                except Exception as e:
                    pass
                check = await check_func(url)
                if (check is False) and (gif is False):
                    check = await self.isgif(url)
                    if check:
                        if msg:
                            await channel.send(
                                ':warning: This command is for images, not gifs (use `gmagik` or `gascii`)!')
                        ctx.command.reset_cooldown(ctx)
                        return False
                    elif len(img_urls) == 0:
                        name = url[8:] if url.startswith('https://') else url[7:]
                        member = self.find_member(message.guild, name, 2)
                        if member:
                            img_urls.append(member.avatar_url_as(format='png', static_format='png') if member.avatar else member.default_avatar_url)
                            count += 1
                            continue
                        if msg:
                            await channel.send(':warning: Unable to download or verify URL is valid.')
                        ctx.command.reset_cooldown(ctx)
                        return False
                    else:
                        if msg:
                            await channel.send(':warning: Image `{0}` is Invalid!'.format(count))
                        continue
                elif gif and (check is False):
                    check = await self.isimage(url)
                    if check:
                        if msg:
                            await channel.send(':warning: This command is for gifs, not images (use `magik`)!')
                        ctx.command.reset_cooldown(ctx)
                        return False
                    elif len(img_urls) == 0:
                        name = url[8:] if url.startswith('https://') else url[7:]
                        member = self.find_member(message.guild, name, 2)
                        if member:
                            img_urls.append(member.avatar_url_as(format='png', static_format='png') if member.avatar else member.default_avatar_url)
                            count += 1
                            continue
                        if msg:
                            await channel.send(':warning: Unable to download or verify URL is valid.')
                        ctx.command.reset_cooldown(ctx)
                        return False
                    else:
                        if msg:
                            await channel.send(':warning: Gif `{0}` is Invalid!'.format(count))
                        continue
                img_urls.append(url)
                count += 1
            else:
                if len(img_urls) == 0:
                    attachment_images = await self.get_attachment_images(ctx, check_func)
                    if attachment_images:
                        img_urls.extend([*attachment_images])
                    else:
                        if msg:
                            await channel.send(':no_entry: Please input url(s){0}or attachment(s).'.format(
                                ', mention(s) ' if (not gif) else ' '))
                        ctx.command.reset_cooldown(ctx)
                        return False
            if scale:
                if len(img_urls) == 0:
                    attachment_images = await self.get_attachment_images(ctx, check_func)
                    if attachment_images:
                        img_urls.extend([*attachment_images])
                    else:
                        if msg:
                            await channel.send(':no_entry: Please input url(s){0}or attachment(s).'.format(
                                ', mention(s) ' if (not gif) else ' '))
                        ctx.command.reset_cooldown(ctx)
                        return False
                return (img_urls, int_scale, scale_msg)
            if img_urls:
                return img_urls
            return False
        except Exception as e:
            print(e)


    def find_member(self, guild, name, steps=2):
        member = None
        match = self.mention_regex.search(name)
        if match:
            member = guild.get_member(match.group('id'))
        if (not member):
            name = name.lower()
            checks = [(lambda m: ((m.name.lower() == name) or (m.display_name.lower() == name))), (
                lambda m: (m.name.lower().startswith(name) or m.display_name.lower().startswith(name) or (m.id == name))
            ), (lambda m: ((name in m.display_name.lower()) or (name in m.name.lower())))]
            for i in range(steps if steps <= len(checks) else len(checks)):
                if i == 3:
                    member = discord.utils.find(checks[1], self.bot.get_all_members())
                else:
                    member = discord.utils.find(checks[i], guild.members)
                if member:
                    break
        return member

    async def bytes_download(self, url: str):
        try:
            with async_timeout.timeout(5):
                async with self.session.get(url) as resp:
                    data = await resp.read()
                    b = BytesIO(data)
                    b.seek(0)
                    return b
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            print(e)
            return False

    async def download(self, url: str, path: str):
        try:
            with async_timeout.timeout(5):
                async with self.session.get(url) as resp:
                    data = await resp.read()
                    with open(path, 'wb') as f:
                        f.write(data)
        except asyncio.TimeoutError:
            return False

    def discord_path(self, path):
        return os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), path)

    def files_path(self, path):
        return self.discord_path('images/' + path)

    def random(self, image=False, ext: str = False):
        h = str(uuid.uuid4().hex)
        if image:
            return '{0}.{1}'.format(h, ext) if ext else h + '.png'
        return h

    def memeTopText(self, img, text, path):
        text = text.upper()

        imageSize = img.size

        fontSize = int(imageSize[1]/5)
        font = ImageFont.truetype("fonts/impact.ttf", fontSize)

        topTextSize = font.getsize(text)

        while topTextSize[0] > imageSize[0]-25:
            fontSize = fontSize - 1
            print(fontSize)
            font = ImageFont.truetype("fonts/impact.ttf", fontSize)
            topTextSize = font.getsize(text)

        draw = ImageDraw.Draw(img)
        textSize = font.getsize(text)
        x = (imageSize[0] - textSize[0])/2
        y=10
        draw.text((x+3,y+3), text, (0,0,0), font=font)
        draw.text((x+3,y-3), text, (0,0,0), font=font)
        draw.text((x-3,y+3), text, (0,0,0), font=font)
        draw.text((x-3,y-3), text, (0,0,0), font=font)
        draw.text((x,y), text, fill='white', font=font)

        img.save(path)
        imgfile = discord.File(path)
        return imgfile

    def memeBottomText(self, img, text, path):
        text = text.upper()

        imageSize = img.size
        
        fontSize = int(imageSize[1]/5)
        font = ImageFont.truetype("fonts/impact.ttf", fontSize)

        topTextSize = font.getsize(text)
        charWidth, charHeight = font.getsize('A')

        charsPerLine = imageSize[0] // charWidth
        bottomLines = textwrap.wrap(text, width = charsPerLine)


        while topTextSize[0] > imageSize[0]-25:
            fontSize = fontSize - 1
            print(fontSize)
            font = ImageFont.truetype("fonts/impact.ttf", fontSize)
            topTextSize = font.getsize(text)

        draw = ImageDraw.Draw(img)
        textSize = font.getsize(text)
        x = (imageSize[0] - textSize[0])/2
        y = imageSize[1] - charHeight * len(bottomLines) - 15
        draw.text((x+3,y+3), text, (0,0,0), font=font)
        draw.text((x+3,y-3), text, (0,0,0), font=font)
        draw.text((x-3,y+3), text, (0,0,0), font=font)
        draw.text((x-3,y-3), text, (0,0,0), font=font)
        draw.text((x,y), text, fill='white', font=font)

        img.save(path)
        imgfile = discord.File(path)
        return imgfile

    def memeTopBottomText(self, img, text, path):
        if '|' not in text:
            textList = text.split(' ')

            length = len(textList)//2

            topString = ' '.join(textList[0:length])
            bottomString = ' '.join(textList[length:])
            topString = topString.upper()
            bottomString = bottomString.upper()
            
        else:
            text = text.split('|')
            topString = text[0].upper()
            bottomString = text[1].upper()

        imageSize = img.size

        # Start with largest font size that could possibly fit
        fontSize = int(imageSize[1]/5)
        font = ImageFont.truetype("fonts/impact.ttf", fontSize)

        # Get width of generic character and how many chars would fit per line
        charWidth, charHeight = font.getsize('A')
        charsPerLine = imageSize[0] // charWidth

        # Wrap the lines based on character width
        topLines = textwrap.wrap(topString, width=charsPerLine)
        bottomLines = textwrap.wrap(bottomString, width = charsPerLine)

        # Get size of top line line of top and bottom
        topTextSize = font.getsize(topLines[0])
        bottomTextSize = font.getsize(bottomLines[0])

        # Calculate the total size of all lines to make sure it isnt too large on picture
        totalTopSize = 0
        for line in topLines:
            height = font.getsize(line)
            totalTopSize += height[1]
        totalBottomSize = 0
        for line in bottomLines:
            height = font.getsize(line)
            totalBottomSize += height[1]

        # Decrease size until it isn't too large for these parameters
        while topTextSize[0] > imageSize[0]-25 or bottomTextSize[0] > imageSize[0]-25 or totalTopSize > imageSize[1]//4 or totalBottomSize > imageSize[1]//4:
            fontSize = fontSize - 1
            font = ImageFont.truetype("fonts/impact.ttf", fontSize)

            # Recalculate total size each iteration
            totalTopSize = 0
            for line in topLines:
                height = font.getsize(line)
                totalTopSize += height[1]
            totalBottomSize = 0
            for line in bottomLines:
                height = font.getsize(line)
                totalBottomSize += height[1]

            # Initialize new font object
            charWidth, charHeight = font.getsize('A')

            charsPerLine = imageSize[0] // charWidth

            topLines = textwrap.wrap(topString, width=charsPerLine)
            bottomLines = textwrap.wrap(bottomString, width = charsPerLine)

            topTextSize = font.getsize(topLines[0])
            bottomTextSize = font.getsize(bottomLines[0])



        # Create draw object
        draw = ImageDraw.Draw(img)

        # Starting a little off the top of the image
        y = 10
        for line in topLines:
            # For every line, draw the black outline first then the white text on top
            line_width, line_height = font.getsize(line)
            x = (imageSize[0] - line_width)/2
            draw.text((x+3,y+3), line, (0,0,0), font=font)
            draw.text((x+3,y-3), line, (0,0,0), font=font)
            draw.text((x-3,y+3), line, (0,0,0), font=font)
            draw.text((x-3,y-3), line, (0,0,0), font=font)
            draw.text((x,y), line, fill='white', font=font)
            # Go to next line
            y += line_height

        # Starting at the bottom
        y = imageSize[1] - charHeight * len(bottomLines) - 15
        for line in bottomLines:
            # For every line, draw black outline first then white text on top
            line_width, line_height = font.getsize(line)
            x = (imageSize[0] - line_width)/2
            draw.text((x+3,y+3), line, (0,0,0), font=font)
            draw.text((x+3,y-3), line, (0,0,0), font=font)
            draw.text((x-3,y+3), line, (0,0,0), font=font)
            draw.text((x-3,y-3), line, (0,0,0), font=font)
            draw.text((x,y), line, fill='white', font=font)
            y += line_height
        
        # Save edited image as 'temp.png' and assign it to discord file object
        img.save("images/temp.png")
        imgfile = discord.File('images/temp.png')
        return imgfile
