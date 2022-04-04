import logging
import os
import re
import sys
import tempfile
from pathlib import Path

import telethon.utils
from PyPDF2 import PdfFileMerger
from dynaconf import Dynaconf
from fpdf import FPDF, HTMLMixin
from markdown2 import Markdown
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

long_message_length = settings.bot.long_message_length


@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Send a message when the command /start is issued."""
    await event.respond('Hi!')
    raise events.StopPropagation


def wget_download(url):
    r = os.system('wget -q {}'.format(url))
    return r


class PDF(FPDF, HTMLMixin):
    pass


async def handle_normal_text(event):
    if len(event.text) >= long_message_length:
        await to_pdf(event)

    urls = utils.parse_urls(event.text)
    await handle_urls(event, urls)


async def handle_urls(event, urls):
    try:
        if len(urls) == 0:
            await event.respond("No URLs are found!")
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
            if not r:
                msg = await event.reply('An error occurred while converting the webpage to PDF!')
            # msg = await msg.edit('{} is downloaded'.format(filename))
            await event.client.send_file(event.chat, r, reply_to=msg)

    except:
        logging.error("Unexpected error:", sys.exc_info()[0])
    finally:
        raise events.StopPropagation


def get_filename(message, prefix):
    file = message.file
    if file and file.name:
        if file.name.endswith(file.ext):
            return file.name
        return file.name + file.ext

    return "{} {}{}".format(prefix, file.media.date, file.ext)


async def download_media(message, prefix):
    download_folder = download_dir
    if message.photo:
        download_folder = os.path.join(download_folder, "chat/{}".format(message.photo.id))
        Path(download_folder).mkdir(parents=True, exist_ok=True)

    filename = get_filename(message, prefix)
    filepath = os.path.join(download_folder, filename)
    target_path = await message.download_media(filepath)

    return target_path


@bot.on(events.Album)
async def on_album(event: events.Album.Event):
    await to_pdf(event)


def get_chat(event):
    if event.chat:
        return event.chat
    return event.messages[0].chat


def get_display_name(event):
    if hasattr(event, 'forward'):
        return telethon.utils.get_display_name(event.forward.chat)

    chat = get_chat(event)
    return telethon.utils.get_display_name(chat)


async def to_pdf(event):
    msg = await event.reply('The message is being converted to PDF')
    chat = get_chat(event)
    display_name = get_display_name(event)

    messages = event.messages if hasattr(event, 'messages') else [event.message]

    fontsize_pt = 10
    margin_bottom_mm = 10

    # A4: 210 x 297 mm
    page_h = (210 - 10) / 2
    page_w = 297
    pdf = PDF(orientation='P', unit='mm', format=(page_h, page_w))

    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../fonts/')
    pdf.add_font('NanumGothicCoding', fname=os.path.join(font_dir, 'NanumGothicCoding-Regular.ttf'))
    pdf.set_font('NanumGothicCoding', size=fontsize_pt)

    # pdf.core_fonts_encoding = 'utf-8'

    # pdf.set_author(display_name)
    # pdf.set_title(title)

    pdf.set_auto_page_break(True, margin=margin_bottom_mm)
    # pdf.oversized_images = "DOWNSCALE"
    pdf.add_page()

    text = ""
    for msg in messages:
        if msg.text:
            text = "{}{}\n\n".format(text, msg.text)

        # if event.message.media is None or isinstance(event.message.media, types.MessageMediaWebPage):
        #     continue

        downloaded_path = await download_media(msg, prefix=display_name)
        # w = msg.photo.sizes[-1].w
        # h = msg.photo.sizes[-1].h
        w = pdf.epw

        pdf.image(downloaded_path, w=w)

    text = text.strip()
    if text:
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../fonts/')
        pdf.add_font('NanumGothicCoding', fname=os.path.join(font_dir, 'NanumGothicCoding-Regular.ttf'))
        # pdf.set_font('NanumGothicCoding', size=fontsize_pt)
        pdf.set_font('NanumGothicCoding')

        pattern = (
            r'((([A-Za-z]{3,9}:(?:\/\/)?)'  # scheme
            r'(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:\[0-9]+)?'  # user@hostname:port
            r'|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)'  # www.|user@hostname
            r'((?:\/[\+~%\/\.\w\-_]*)?'  # path
            r'\??(?:[\-\+=&;%@\.\w_]*)'  # query parameters
            r'#?(?:[\.\!\/\\\w]*))?)'  # fragment
            r'(?![^<]*?(?:<\/\w+>|\/?>))'  # ignore anchor HTML tags
            r'(?![^\(]*?\))'  # ignore links in brackets (Markdown links and images)
        )
        link_patterns = [(re.compile(pattern), r'\1')]
        markdown = Markdown(extras=["link-patterns"], link_patterns=link_patterns)
        html_text = markdown.convert(text)
        pdf.write_html(html_text)

    title = get_title(event, text)
    # pdf.set_title(title)

    filename = '{}{}'.format(event.original_update.message.date, '.pdf')
    # filename = '{}{}'.format(title, '.pdf')
    filepath = os.path.join(download_dir, filename)
    pdf.output(filepath)

    renamed_filename = '{}{}'.format(title, '.pdf')
    renamed_filepath = os.path.join(download_dir, renamed_filename)

    # pdf.set_title(), pdf.set_author() 가 유니코드 처리를 못 해서 다른 라이브러리로 밀어넣는다.
    save_pdf(filepath, renamed_filepath, display_name, title)

    await event.client.send_file(chat, renamed_filepath, reply_to=msg)


def save_pdf(input_pdf: str, output_pdf: str, author: str, title: str):
    file_in = open(input_pdf, 'rb')

    pdf_merger = PdfFileMerger()
    pdf_merger.append(file_in)
    pdf_merger.addMetadata({
        '/Author': author,
        '/Title': title
    })
    file_out = open(output_pdf, 'wb')
    pdf_merger.write(file_out)

    file_in.close()
    file_out.close()


def get_title(event, text):
    if hasattr(event, 'message'):
        file = event.message.file
        if file and file.name:
            if file.name.endswith(file.ext):
                return file.name[:-len(file.ext)]
            return file.name

    display_name = get_display_name(event)

    if text:
        first_line = text.splitlines()[0]
        title_len = min(len(first_line), 32)
        return "{} by {}".format(first_line[:title_len], display_name)

    return "{} {}".format(display_name, event.original_update.message.date)


@bot.on(events.NewMessage)
async def on_single_msg(event):
    # Album should be handled by the function on_album
    if event.grouped_id:
        return

    if event.message.media is None or isinstance(event.message.media, types.MessageMediaWebPage):
        await handle_normal_text(event)
        return

    if isinstance(event.message.media, types.MessageMediaPhoto):
        await to_pdf(event)
        return

    if isinstance(event.message.media,
                  types.MessageMediaDocument) and event.message.media.document.mime_type.startswith('image/'):
        await to_pdf(event)
        return

    await event.reply("Visit https://github.com/unchartedsky/pdfthis and learn how this bot works.")
    raise events.StopPropagation


def get_bot():
    return bot
