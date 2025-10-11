from telebot import TeleBot, types
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from database import DataBase
import os
from datetime import datetime

load_dotenv()

class Bot:
    def __init__(self):
        self.bot = TeleBot(token=os.getenv("TOKEN"))
        self.db = DataBase()
        self.app = Flask(__name__)
        CORS(self.app, origins="*")

        self._register_handlers()
        self._register_apis()
        self._register_webhook()
        
        self._setup_webhook()

    # ------------------- Handlers -------------------
    def _register_handlers(self):
        self.bot.register_message_handler(self.show_menu, commands=['start'])
        self.bot.register_message_handler(self.instructions, commands=['help'])

    # ------------------- API Routes -------------------
    def _register_apis(self):
        self.app.route("/get_user", methods=['GET'])(self.get_user)
        self.app.route("/create_user", methods=['POST'])(self.create_user)
        self.app.route("/get_purchases", methods=['GET'])(self.get_purchases)
        self.app.route("/ping", methods=['GET'])(self.ping)
        self.app.route("/points/sum", methods=["GET"])(self.get_sum_points)
        self.app.route("/points/history", methods=["GET"])(self.get_history_points)
        self.app.route("/points/referral", methods=['GET'])(self.get_referals_points)
        self.app.route("/referral_link", methods=["PUT"])(self.put_referral_link)

    # ------------------- Webhook -------------------
    def _register_webhook(self):
        @self.app.route("/webhook", methods=["POST"])
        def webhook():
            json_data = request.get_data().decode("utf-8")
            update = types.Update.de_json(json_data)
            self.bot.process_new_updates([update])
            return "OK", 200

    # ------------------- API Handlers -------------------
    def get_purchases(self):
        user_id = request.args.get('id')
        data = self.db.get_data(table="purchases", column="id", element=user_id)
        return jsonify(data)

    def ping(self):
        return jsonify({"status": "ok", "message": "Flask API работает ✅"})

    def get_user(self):
        user_id = request.args.get('id')
        user = self.db.get_data(column="id", element=user_id)
        return jsonify(user)

    def create_user(self):
        data = request.get_json()
        self.db.insert_data(table="users", data=data)
        return jsonify({"status": "success", "data": data})

    def get_sum_points(self):
        user_id = request.args.get('id')
        user = self.db.get_data(table="points", column="id", element=user_id)
        return jsonify({"sum_points": sum([elem.get("count") for elem in user])})

    def get_history_points(self):
        user_id = request.args.get('id')
        user = self.db.get_data(table="points", column="id", element=user_id)
        return jsonify({"data": user})

    def get_referals_points(self):
        user_id = request.args.get('id')
        user = self.db.get_data(table="points", column="id", element=user_id)
        return jsonify({"sum_points": [elem.get("count") for elem in user]})

    def put_referral_link(self):
        json_data = request.get_json()
        user_id = json_data.get('id')
        referral_link = json_data.get('referral_link')

        if not user_id or not referral_link:
            return jsonify({"status": "error", "message": "id или referral_link отсутствует"}), 400

        updated = self.db.update_data(
            table="users",
            match_column="id",
            match_value=user_id,
            data={"referal_link": referral_link} 
        )
        return jsonify({"status": "success", "data": updated})

    # ------------------- Bot Handlers -------------------
    def show_menu(self, message):        
        referrer_id = None
        if message.text.startswith('/start '):
            payload = message.text.split(' ')[1]
            if payload.isdigit(): 
                referrer_id = int(payload)
        user_id = message.from_user.id
        response = self.db.get_data(column="id", element=user_id)
        
        if not response:
            self.db.insert_data(table="users", data={
                "id": user_id,
                "username": message.from_user.username,
                "referred_by": referrer_id 
            })
            if referrer_id:
                self.db.insert_data(table="points", data={
                    "id": referrer_id, 
                    "count": 150, 
                    "for_this": "Реферальная ссылка", 
                    "date": datetime.now().strftime("%d.%m.%Y") 
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

    def _setup_webhook(self):
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url and not os.getenv("DEBUG"):
            self.bot.remove_webhook()
            self.bot.set_webhook(url=f"{webhook_url}/webhook")
            print(f"Webhook установлен: {webhook_url}/webhook")
            
    def start_flask(self):
        debug = os.getenv("DEBUG", "False").lower() == "true"
        port = int(os.environ.get("PORT", 5000))
        self.app.run(host="0.0.0.0", port=port, debug=debug)

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

    # ------------------- Запуск -------------------
    def start_flask(self):
        self.app.run(port=5000, debug=True, use_reloader=False)

if __name__ == "__main__":
    bot = Bot()
    bot.start_flask()
