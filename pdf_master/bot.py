import logging
import os
import sys
import tempfile
from pathlib import Path

import telethon.utils
from PyPDF2 import PdfFileMerger
from dynaconf import Dynaconf
from fpdf import FPDF, HTMLMixin
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

client = TelegramClient('pdfthis', api_id, api_hash)
client.parse_mode = 'html'
bot = client.start(bot_token=bot_token)

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

    # event.text 는 마크업을 포함하기 때문에 event.message.message를 사용한다
    urls = utils.parse_urls(event.message.message)
    await handle_urls(event, urls)


def is_unsupported(url):
    urls_unsupported = [
        'truefriend.com',
        'github.com/unchartedsky/pdfthis'
    ]

    for url_unsupported in urls_unsupported:
        if url_unsupported in url:
            return True

    return False


async def handle_urls(event, urls):
    try:
        if len(urls) == 0:
            await event.respond("No URLs are found!")
            return

        for url in urls:
            if is_unsupported(url):
                msg = await event.reply('The site is not supported yet: {}'.format(url))
                continue

            _logger.info('URL is being handled: {}'.format(url))

            if 'drive.google.com' in url.lower():
                msg = await event.reply('File is being downloaded from Google Drive...')
                url = url.replace('usp=drivesdk', 'usp=sharing')
                # TODO 로컬 경로가 겹칠 수 있을 듯
                r = utils.gdown_better(url, cwd=download_dir)
                if not r:
                    continue

                _logger.info('file download is done: {}'.format(r))
                # msg = await msg.edit('{} is downloaded'.format(filename))
                await event.client.send_file(event.chat, r, reply_to=msg)
                continue

            filename = utils.get_pdf_filename(url)
            if filename:
                msg = await event.reply('{} is being downloaded...'.format(filename))
                r = utils.wget_better(url, cwd=download_dir)
                if not r:
                    continue

                _logger.info('file download is done: {}'.format(r))
                # msg = await msg.edit('{} is downloaded'.format(filename))
                await event.client.send_file(event.chat, r, reply_to=msg)
                continue

            msg = await event.reply('The web page is being converted to PDF')
            files = utils.to_pdf(url, cwd=download_dir)
            if not files and len(files) > 0:
                msg = await event.reply('An error occurred while converting the webpage to PDF!')
            # msg = await msg.edit('{} is downloaded'.format(filename))
            for file in files:
                await event.client.send_file(event.chat, file, reply_to=msg)

    except:
        logging.error("Unexpected error:", sys.exc_info()[0])
    finally:
        raise events.StopPropagation


def get_filename(message, prefix):
    file = message.file
    if file and file.name:
        if file.name.endswith(file.ext):
            return utils.slugify_better(file.name)
        return "{}{}".format(
            utils.slugify_better(file.name),
            file.ext
        )

    filename = utils.slugify_better(
        "{} {}".format(prefix, file.media.date)
    )
    return "{}{}".format(filename, file.ext)


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

    # fontsize_pt = 10
    margin_bottom_mm = 10

    # A4: 210 x 297 mm
    page_h = 210 * 2 / 3
    page_w = 297
    pdf = PDF(orientation='P', unit='mm', format=(page_h, page_w))

    # font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../fonts/')
    # pdf.add_font('NanumGothicCoding', fname=os.path.join(font_dir, 'NanumGothicCoding-Regular.ttf'))
    # pdf.set_font('NanumGothicCoding', size=fontsize_pt)

    # pdf.core_fonts_encoding = 'utf-8'

    # pdf.set_author(display_name)
    # pdf.set_title(title)

    pdf.set_auto_page_break(True, margin=margin_bottom_mm)
    # pdf.oversized_images = "DOWNSCALE"
    pdf.add_page()

    text_merged = ""
    msg_merged = ""
    for msg in messages:
        # text: Markdown, html 등 마크업 포함
        if msg.text:
            text_merged = "{}{}\n\n".format(text_merged, msg.text)
        if msg.message:
            msg_merged = "{}{}\n\n".format(msg_merged, msg.message)

        if msg.media is None or isinstance(msg.media, types.MessageMediaWebPage):
            continue

        downloaded_path = await download_media(msg, prefix=display_name)
        # w = msg.photo.sizes[-1].w
        # h = msg.photo.sizes[-1].h
        w = pdf.epw

        pdf.image(downloaded_path, w=w)

    text_merged = text_merged.strip()
    if text_merged:
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../fonts/')
        pdf.add_font('NanumGothicCoding', fname=os.path.join(font_dir, 'NanumGothicCoding-Regular.ttf'))
        pdf.add_font('NanumGothicCoding', style='B', fname=os.path.join(font_dir, 'NanumGothicCoding-Bold.ttf'))
        pdf.add_font('NanumGothicCoding', style='I', fname=os.path.join(font_dir, 'NanumGothicCoding-Regular.ttf'))
        # pdf.set_font('NanumGothicCoding', size=fontsize_pt)
        pdf.set_font('NanumGothicCoding')

        patterns = [
            ('<strong>', '<b>'),
            ('</strong>', '</b>'),
            ('<em>', '<i>'),
            ('</em>', '</i>'),
            ('\n', '<br /><br />')
        ]
        html_text = text_merged
        for pattern in patterns:
            o, c = pattern
            html_text = html_text.replace(o, c)
        pdf.write_html(html_text)

    msg_merged = msg_merged.strip()
    title = get_title(event, msg_merged)
    # pdf.set_title(title)

    filename = "{}; {}".format(
        event.original_update.message.date,
        display_name
    )
    filename = "{}.pdf".format(
        utils.slugify_better(filename)
    )
    # filename = '{}{}'.format(title, '.pdf')
    filepath = os.path.join(download_dir, filename)
    pdf.output(filepath)

    renamed_filename = "{}; {}".format(
        title,
        display_name
    )
    renamed_filename = '{}.pdf'.format(
        utils.slugify_better(renamed_filename)
    )
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

    if text:
        first_line = text.splitlines()[0]
        title_len = min(len(first_line), 32)
        return "{}".format(first_line[:title_len])

    display_name = get_display_name(event)
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
