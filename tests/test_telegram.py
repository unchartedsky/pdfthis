import unittest

from dynaconf import Dynaconf
from telethon import TelegramClient, events


class Telegram(unittest.TestCase):
    def test_send_(self):
        settings = Dynaconf(
            envvar_prefix="PDFTHIS",
            settings_files=['settings.yaml', '.secrets.yaml'],
        )

        api_id = settings.telegram.api_id
        api_hash = settings.telegram.api_hash
        bot_token = settings.telegram.bot_token

        bot = TelegramClient('tywin', api_id, api_hash).start(bot_token=bot_token)

        @bot.on(events.NewMessage(pattern='/start'))
        async def start(event):
            """Send a message when the command /start is issued."""
            await event.respond('Hi!')
            raise events.StopPropagation

        # client.start()
        with bot:
            self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
