# -*- coding: utf-8 -*-

from config import token # Импорт токена
from model import StyleTransferModel
from io import BytesIO
import logging
import torch
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)
PHOTO_1, PHOTO_2 = range(2)
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info('Device: ' + str(device))

dict_cis = dict()

def start(update, context):
    global photo_1_file, photo_2_file, content_image_stream, style_image_stream, output_stream, model
    model = StyleTransferModel()
    content_image_stream = BytesIO()
    style_image_stream = BytesIO()
    output_stream = BytesIO()
    update.message.reply_text(
        'Хочешь я круто стилизую твое фото?\n'
        'Высылай фото для стилизации!'
    )
    return PHOTO_1

def photo_1(update, context):
    user = update.message.from_user
    photo_1_file = update.message.photo[-1].get_file()
    photo_1_file.download(out=content_image_stream)
    dict_cis[str(user.name)] = content_image_stream
    logger.info('Фото контента получено: ' + str(user.name) + ' ' + str(photo_1_file.file_path[-6:]) + ' ' + str(photo_1_file.file_size))
    update.message.reply_text('Получено.\n'
                              'Теперь пришли мне картинку, у которой я могу перенять стиль!')
    # первая картинка, которая к нам пришла станет content image, а вторая style image
    return PHOTO_2

def photo_2(update, context):
    user = update.message.from_user
    photo_2_file = update.message.photo[-1].get_file()
    photo_2_file.download(out=style_image_stream)
    logger.info('Фото стиля получено: ' + str(user.name) + ' ' + str(photo_2_file.file_path[-6:]) + ' ' + str(photo_2_file.file_size))
    update.message.reply_text('Отлично!\n'
                              'Подожди чуть-чуть (2-3 минуты) и я пришлю тебе результат!')
    # найти content_image_stream
    content_image_stream = dict_cis[str(user.name)]
    del dict_cis[str(user.name)]
    # первая картинка, которая к нам пришла станет content image, а вторая style image
    output = model.transfer_style(content_image_stream, style_image_stream)
    # теперь отправим назад фото
    chat_id = update.message.chat_id
    output.save(output_stream, format='PNG')
    output_stream.seek(0)
    context.bot.send_photo(chat_id, photo=output_stream, caption='Посмотри что получилось. Для повторного запуска используй /start')
    logger.info('Результат выслан: ' + str(user.name))
    return ConversationHandler.END

def skip_photo(update, context):
    user = update.message.from_user
    logger.info("Пользователь %s не прислал фото", user.first_name)
    update.message.reply_text('Без фото я не смогу ничего сделать!')
    return ConversationHandler.END

def cancel(update, context):
    user = update.message.from_user
    logger.info("Пользователь %s прервал общение", user.first_name)
    update.message.reply_text('Пока! Будешь в наших краях - заходи.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Обновление "%s" вызвало ошибку "%s"', update, context.error)

def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    #updater = Updater(token=token, use_context=True,  request_kwargs={'proxy_url': 'socks5h://163.172.152.192:1080'})
    updater = Updater(token=token, use_context=True)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTO_1: [MessageHandler(Filters.photo, photo_1)
                , CommandHandler('start', start)
                , CommandHandler('skip', skip_photo)],
            PHOTO_2: [MessageHandler(Filters.photo, photo_2)
                , CommandHandler('start', start)
                , CommandHandler('skip', skip_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    # log all errors
    dp.add_error_handler(error)
    # Start the Bot
    updater.start_polling()
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()