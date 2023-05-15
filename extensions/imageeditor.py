import os, disnake, asyncio, requests, textwrap, re, math
from io import BytesIO, StringIO
import numpy as np

import PIL
from PIL import Image

from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from utils.funcs import Funcs

# import PIL
# from PIL import Image, ImageFont, ImageDraw

import subprocess

import wand
# from wand.image import Image

code = "```py\n{0}\n```"


class ImageEdit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        funcs = Funcs(bot)
        self.get_images = funcs.get_images
        self.isimage = funcs.isimage
        self.isgif = funcs.isgif
        self.find_member = funcs.find_member
        self.files_path = funcs.files_path
        self.download = funcs.download
        self.random = funcs.random
        self.bytes_download = funcs.bytes_download

        self.memeTopText = funcs.memeTopText
        self.memeBottomText = funcs.memeBottomText
        self.memeTopBottomText = funcs.memeTopBottomText

    @commands.Cog.listener()
    async def on_ready(self):
        print('ImageEdit is loaded')

        
    @commands.command()
    async def meme(self, ctx, *args):
        try:
            url = list(args)[0]
            if url.startswith('http'):
                args = list(args)
                args.pop(0)
                # args = tuple(args)
                get_images = await self.get_images(ctx, urls=url, limit=1)
            else:
                get_images = await self.get_images(ctx, urls=None)
            if not get_images:
                    await ctx.channel.send("No image found")
                    return
            for url in get_images:
                path = self.files_path(self.random(True))
                await self.download(url, path)
                img = Image.open(path)
                # Check that text isnt just 1 word (if it is, go straight to top only method)
                if (args[0] == "|"):
                        args = list(args)
                        args.pop(0)
                        text = ' '.join(args)
                        imgfile = self.memeBottomText(img, text, path)
                else:
                        text = ' '.join(args)
                        if len(args) == 1 or args[-1] == '|':
                                if args[-1] == '|':
                                        args = list(args)
                                        args.pop(-1)
                                        text = ' '.join(args)
                                imgfile = self.memeTopText(img, text, path)
                        else:
                                imgfile = self.memeTopBottomText(img, text, path)
                await ctx.send(file = imgfile)
	            # Cleanup
                os.remove(path)
        except:
            try:
                os.remove(path)
            except:
                pass
            raise


    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def buldge(self, ctx, *urls:str):
        try:
            get_images = await self.get_images(ctx, urls=urls)
            if not get_images:
                return
            for url in get_images:
                path = self.files_path(self.random(True))
                await self.download(url, path)
                cmd = ['convert', '(', path, ')', '-implode', '-2', path]
                try:
                    subprocess.run(cmd, timeout=15)
                    await ctx.send(file=disnake.File(path))
                except TimeoutError:
                    ctx.channel.send('Process timed out, try again later.')
                except Exception as e:
                    print(e)
                os.remove(path)
        except:
            try:
                os.remove(path)
            except:
                pass
            raise
    
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def implode(self, ctx, *urls:str):
        try:
            get_images = await self.get_images(ctx, urls=urls)
            if not get_images:
                return
            for url in get_images:
                path = self.files_path(self.random(True))
                await self.download(url, path)
                cmd = ['convert', '(', path, ')', '-implode', '.5', path]
                try:
                    subprocess.run(cmd, timeout=15)
                    await ctx.send(file=disnake.File(path, filename='implode.png'))
                except TimeoutError:
                    ctx.channel.send('Process timed out, try again later.')
                except Exception as e:
                    print(e)
                os.remove(path)
        except:
            try:
                os.remove(path)
            except:
                pass
            raise

#    def do_magik(self, scale, *imgs):
#        try:
#            list_imgs = []
#            exif = {}
#            exif_msg = ''
#            count = 0
#            for img in imgs:
#                i = wand.image.Image(file=img)
#                i.format = 'jpg'
#                i.alpha_channel = True
#                if i.size >= (3000, 3000):
#                    return ':warning: `Image exceeds maximum resolution >= (3000, 3000).`', None
#                exif.update({count:(k[5:], v) for k, v in i.metadata.items() if k.startswith('exif:')})
#                count += 1
#                i.transform(resize='800x800>')
#                i.liquid_rescale(width=int(i.width * 0.5), height=int(i.height * 0.5), delta_x=int(0.5 * scale) if scale else 1, rigidity=0)
#                i.liquid_rescale(width=int(i.width * 1.5), height=int(i.height * 1.5), delta_x=scale if scale else 2, rigidity=0)
#                magikd = BytesIO()
#                i.save(file=magikd)
#                magikd.seek(0)
#                list_imgs.append(magikd)
#            if len(list_imgs) > 1:
#                imgs = [PIL.Image.open(i).convert('RGBA') for i in list_imgs]
#                min_shape = sorted([(np.sum(i.size), i.size) for i in imgs])[0][1]
#                imgs_comb = np.hstack((np.asarray(i.resize(min_shape)) for i in imgs))
#                imgs_comb = PIL.Image.fromarray(imgs_comb)
#                ya = BytesIO()
#                imgs_comb.save(ya, 'png')
#                ya.seek(0)
#            elif not len(list_imgs):
#                return ':warning: **Command download function failed...**', None
#            else:
#                ya = list_imgs[0]
#            for x in exif:
#                if len(exif[x]) >= 2000:
#                    continue
#                exif_msg += '**Exif data for image #{0}**\n'.format(str(x+1))+code.format(exif[x])
#            else:
#                if len(exif_msg) == 0:
#                    exif_msg = None
#            return ya, exif_msg
#        except Exception as e:
#            return str(e), None

#    @commands.command()
#    async def magick(self, ctx, *urls:str):
#        get_images = await self.get_images(ctx, urls=urls, limit=6, scale=5)
#        if not get_images:
#            return
#        img_urls = get_images[0]
#        scale = get_images[1]
#        scale_msg = get_images[2]
#        if scale_msg is None:
#            scale_msg = ''
#        msg = await ctx.message.channel.send("ok, processing")
#        list_imgs = []
#        for url in img_urls:
#            b = await self.bytes_download(url)
#            if b is False:
#                if len(img_urls) > 1:
#                    await ctx.send(':warning: **Command download function failed...**')
#                    return
#                continue
#            list_imgs.append(b)
#        final, content_msg = await self.bot.loop.run_in_executor(None, self.do_magik, scale, *list_imgs)
#        if type(final) == str:
#            await ctx.send(final)
#            return
#        if content_msg is None:
#            content_msg = scale_msg
#        else:
#            content_msg = scale_msg+content_msg
#        await msg.delete()
#        await ctx.send(file=discord.File(final, filename='magik.png'), content=content_msg)
        # except discord.errors.Forbidden:
        # await ctx.send(":warning: **I do not have permission to send files!**")

    #@commands.slash_command()
    async def rotate(self, inter: ApplicationCommandInteraction, image=None):
        """Rotate an image 90 degrees."""
        get_images = await self.get_images(inter, image)

        if not get_images:
            return
        for url in get_images:
            path = self.files_path(self.random(True))
            await self.download(url, path)
            cmd = ['convert', '(', path, ')', '-rotate', '90', path]
            try:
                subprocess.run(cmd, timeout=10)
                await ctx.send(file=disnake.File(path, filename='implode.png'))
            except TimeoutError:
                inter.response.send_message('Process timed out, try again later.', ephemeral=True)
            except Exception as e:
                print(e)
                os.remove(path)

        try:
            os.remove(path)
        except:
            pass
        raise


def setup(bot):
    bot.add_cog(ImageEdit(bot))
