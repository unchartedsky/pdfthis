import logging
import os
import tempfile

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

        tmpdir = tempfile.mkdtemp()
        for url in urls:
            filename = utils.get_pdf_filename(url)
            if filename:
                msg = await event.reply('{} is being downloaded...'.format(filename))
                r = utils.wget_better(url, cwd=tmpdir)
                # msg = await msg.edit('{} is downloaded'.format(filename))
                await event.client.send_file(event.chat, r, reply_to=msg)
                continue

            msg = await event.reply('The web page is being converted to PDF')
            r = utils.percollate(url)
            # msg = await msg.edit('{} is downloaded'.format(filename))
            await event.client.send_file(event.chat, r, reply_to=msg)

    # except:
    #     logging.error("Unexpected error:", sys.exc_info()[0])
    #     raise
    finally:
        raise events.StopPropagation


@bot.on(events.NewMessage)
async def echo(event):
    if event.message.media is None or isinstance(event.message.media, types.MessageMediaWebPage):
        await handle_normal_text(event)
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
