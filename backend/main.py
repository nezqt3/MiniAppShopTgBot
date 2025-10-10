from telebot import TeleBot
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from database import DataBase
import os
import threading

load_dotenv()

class Bot:
    def __init__(self):
        self.bot = TeleBot(token=os.getenv("TOKEN"))
        self.db = DataBase()
        self.app = Flask(__name__)
        CORS(self.app, origins="*")  # Разрешаем все источники для dev

        self._register_handlers()
        self._register_apis()

        threading.Thread(
            target=lambda: self.app.run(port=5000, debug=True, use_reloader=False)
        ).start()

    def _register_handlers(self):
        self.bot.register_message_handler(self.show_menu, commands=['start'])
        self.bot.register_message_handler(self.instructions, commands=['help'])

    def _register_apis(self):
        self.app.route("/get_user", methods=['GET'])(self.get_user)
        self.app.route("/create_user", methods=['POST'])(self.create_user)
        self.app.route("/get_purchases", methods=['GET'])(self.get_purchases)
        self.app.route("/ping", methods=['GET'])(self.ping)

    def get_purchases(self):
        user_id = request.args.get('id')
        data = self.db.get_data(table="purchases", column="id", element=user_id)
        return jsonify(data)
    
    def ping(self):
        return jsonify({
            "status": "ok",
            "message": "Flask API работает ✅",
        })

    def get_user(self):
        user_id = request.args.get('id')
        user = self.db.get_data(column="id", element=user_id)
        return jsonify(user)

    def create_user(self):
        data = request.get_json()
        self.db.insert_data(table="users", data=data)
        return jsonify({"status": "success", "data": data})

    def show_menu(self, message):
        response = self.db.get_data(column="id", element=message.from_user.id)
        if not response:
            self.db.insert_data(table="users", data={
                "id": message.from_user.id,
                "username": message.from_user.username
            })

        self.bot.send_message(
            message.chat.id,
            text=(
                "👋 Привет!\n"
                "Тебя приветствует бот магазина Ghost404 🎁\n\n"
                "Вот что ты можешь сделать:\n"
                "• /start — вывести стартовое сообщение\n"
                "• /help — написать нашему менеджеру\n\n"
                "Также ты можешь открыть приложение, чтобы посмотреть всю информацию о своих баллах и рефералах.\n\n"
                "Вместе копить баллы — весело и выгодно! 🚀"
            ),
            parse_mode="Markdown"
        )

    def instructions(self, message):
        self.bot.send_message(
            message.chat.id,
            text=(
                "💡 Краткие инструкции для удобной работы:\n\n"
                "1️⃣ Вся информация о ваших баллах и рефералах доступна только в приложении.\n"
                "2️⃣ Если у вас возникли вопросы или проблемы, напишите нашему менеджеру — @ghostedmng"
            ),
            parse_mode="Markdown"
        )

    def start_bot(self):
        self.bot.infinity_polling()


if __name__ == "__main__":
    bot = Bot()
    threading.Thread(target=bot.start_bot).start()
