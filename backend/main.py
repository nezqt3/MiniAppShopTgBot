from telebot import *
import urllib.parse
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

last_users = []
points = {}
referrals = {}

class Bot(object):
    def __init__(self):
        self.bot = TeleBot(token=os.getenv("TOKEN"))
        self._register_handler()
        self.app = Flask(__name__)
        CORS(self.app)

        self._register_apis()

        import threading
        threading.Thread(target=lambda: self.app.run(port=5000, debug=True, use_reloader=False)).start()
        
    def _register_handler(self):
        self.bot.register_message_handler(self.show_menu, commands=['start'])
        self.bot.register_message_handler(self.instructions, commands=['help'])
        
    def _register_apis(self):
        self.app.route("/last_users", methods=['GET'])(self.get_last_user)
        
    def get_last_user(self):
        if last_users:
            return jsonify(last_users[-1])
        return jsonify({})
        
    def show_menu(self, message):
        self.bot.send_message(
            message.chat.id,
            text=(
                "👋 Привет!"
                "Тебя приветствует бот магазина SuperShop 🎁\n"

                "Вот что ты можешь сделать:"
                "• /start — вывести стартовое сообщение"
                "• /help — написать нашему менеджеру"

                "Также ты можешь открыть приложение, чтобы посмотреть всю информацию о своих баллах и рефералах."

                "Вместе копить баллы — весело и выгодно! 🚀"
            ),
            parse_mode="Markdown"
        )
        
    def instructions(self, message):
        self.bot.send_message(message.chat.id, 
            text=(
            "💡 Краткие инструкции для удобной работы:"
            "1️⃣ Вся информация о ваших баллах и рефералах доступна только в приложении."
            "2️⃣ Если у вас возникли вопросы или проблемы, напишите нашему менеджеру — @ghostedmng"
        ),
            parse_mode="Markdown"
        )

        
    def start_bot(self):
        self.bot.infinity_polling()
        

if __name__ == "__main__":
    import threading
    bot = Bot()
    threading.Thread(target=bot.start_bot).start()