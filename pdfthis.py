import logging.config

import pdf_master.bot

logging.config.fileConfig('logging.conf')
_logger = logging.getLogger()

if __name__ == '__main__':
    _logger.info("Starting...")
    bot = pdf_master.bot.get_bot()
    with bot:
        bot.run_until_disconnected()
