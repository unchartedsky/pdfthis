import logging
import os
import sys
import tempfile
from pathlib import Path

from PIL import Image
from dynaconf import Dynaconf
from telethon import TelegramClient, events
from telethon.tl import types

from pdf_master import utils

_logger = logging.getLogger()

settings = Dynaconf(
    envvar_prefix="PDFTHIS",
    settings_files=['settings.yaml', '.secrets.yaml'],
)

api_id = settings.telegram.api_id
api_hash = settings.telegram.api_hash
bot_token = settings.telegram.bot_token

bot = TelegramClient('pdfthis', api_id, api_hash).start(bot_token=bot_token)

download_dir = settings.bot.download_dir if settings.bot.download_dir else tempfile.mkdtemp()
if not os.path.exists(download_dir):
    os.mkdir(download_dir)


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Send a message when the command /start is issued."""
    await event.respond('Hi!')
    raise events.StopPropagation


def wget_download(url):
    r = os.system('wget -q {}'.format(url))
    return r


async def handle_normal_text(event):
    try:
        urls = utils.parse_urls(event.text)
        if len(urls) == 0:
            await event.respond("No URLs are found!")
            return

        if not isinstance(event.chat, types.User):
            await event.respond('You are not registered!')
            return

        for url in urls:
            _logger.info('URL is being handled: {}'.format(url))

            if 'drive.google.com' in url:
                msg = await event.reply('Downloading from Google Drive is not supported yet!')
                # r = gdown.download(url, quiet=False)
                continue

            filename = utils.get_pdf_filename(url)
            if filename:
                msg = await event.reply('{} is being downloaded...'.format(filename))
                r = utils.wget_better(url, cwd=download_dir)
                if not r:
                    _logger.error("wget_better has failed.")
                    continue

                _logger.info('file download is done: {}'.format(r))
                # msg = await msg.edit('{} is downloaded'.format(filename))
                await event.client.send_file(event.chat, r, reply_to=msg)
                continue

            msg = await event.reply('The web page is being converted to PDF')
            r = utils.percollate(url, cwd=download_dir)
            # msg = await msg.edit('{} is downloaded'.format(filename))
            await event.client.send_file(event.chat, r, reply_to=msg)

    except:
        logging.error("Unexpected error:", sys.exc_info()[0])
        raise
    finally:
        raise events.StopPropagation


def get_filename(event):
    file = event.message.file
    if file.name:
        if file.name.endswith(file.ext):
            return file.name
        return file.name + file.ext

    return "{}{}".format(file.media.date, file.ext)


async def handle_photo(event):
    try:
        # photo = event.message.media.photo
        # if not photo:
        #     await event.respond("No Photos are found!")
        #     return

        filename = get_filename(event)
        filepath = os.path.join(download_dir, filename)
        target_path = await event.message.download_media(filepath)

        # target_path = await event.message.download_media()
        # print(target_path)
        pdfname = '{}{}'.format(Path(target_path).resolve().stem, '.pdf')
        pdfpath = os.path.join(download_dir, pdfname)

        # with open(pdfpath, "wb") as f:
        #     f.write(img2pdf.convert(target_path))
        # Creating Image File Object
        with Image.open(target_path) as im:
            # Cheaking if Image File is in 'RGBA' Mode
            if im.mode == "RGBA":
                # If in 'RGBA' Mode Convert to 'RGB' Mode
                im = im.convert("RGB")
                # Converting and Saving file in PDF format
            im.save(pdfpath, "PDF")

        await event.client.send_file(event.chat, pdfpath)

    except:
        logging.error("Unexpected error:", sys.exc_info()[0])
        raise
    finally:
        raise events.StopPropagation


@bot.on(events.NewMessage)
async def echo(event):
    if event.message.media is None or isinstance(event.message.media, types.MessageMediaWebPage):
        await handle_normal_text(event)
        return

    if isinstance(event.message.media, types.MessageMediaPhoto):
        await handle_photo(event)
        return

    if isinstance(event.message.media, types.MessageMediaDocument) and event.message.media.document.mime_type.startswith('image/'):
        await handle_photo(event)
        return

    await event.reply("Visit https://github.com/unchartedsky/pdfthis and learn how this bot works.")
    raise events.StopPropagation

    # file_name = 'unknown name';
    # attributes = event.message.media.document.attributes
    # for attr in attributes:
    #     if isinstance(attr, types.DocumentAttributeFilename):
    #         file_name = attr.file_name
    # _logger.info("[%s] Download queued at %s" % (file_name, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
    # message = await event.reply('In queue')
    # await queue.put([event, message])


def get_bot():
    return bot
