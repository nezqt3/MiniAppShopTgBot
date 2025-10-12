from telebot import TeleBot, types
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from database import DataBase
import os
import hmac
import hashlib
import time
import threading
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
        
    def _register_handlers(self):
        self.bot.register_message_handler(self.show_menu, commands=['start'])
        self.bot.register_message_handler(self.instructions, commands=['help'])

    def _register_apis(self):
        self.app.route("/get_user", methods=['GET'])(self.get_user)
        self.app.route("/create_user", methods=['POST'])(self.create_user)
        self.app.route("/get_purchases", methods=['GET'])(self.get_purchases)
        self.app.route("/ping", methods=['GET'])(self.ping)
        self.app.route("/points/sum", methods=["GET"])(self.get_sum_points)
        self.app.route("/points/history", methods=["GET"])(self.get_history_points)
        self.app.route("/referral_link", methods=["PUT"])(self.put_referral_link)
        self.app.route("/bot", methods=["POST"])(self.webhook)

    def webhook():
        json_str = request.get_data().decode("utf-8")
        update = types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "ok", 200

    def get_purchases(self):
        user_id = request.args.get('id')
        data = self.db.get_data(table="purchases", column="id", element=user_id)
        return jsonify(data)

    def verify_telegram_init_data(init_data: str, bot_token: str):
        try:
            data_parts = init_data.split("&")
            data_dict = dict(part.split("=") for part in data_parts)
            hash_from_telegram = data_dict.pop("hash")
            data_check_string = "\n".join(f"{k}={v}" for k,v in sorted(data_dict.items()))
            secret_key = hashlib.sha256(bot_token.encode()).digest()
            hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
            return hmac_hash == hash_from_telegram
        except Exception:
            return False

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

    def get_photo_url_by_id(self, user_id):
        user_data = self.db.get_data(table="users", column="id", element=user_id)
        if user_data and len(user_data) > 0:
            return user_data[0].get("photo_url")
        return None

    def get_history_points(self):
        user_id = request.args.get('id')
        points = self.db.get_data(table="points", column="id", element=user_id)
        enriched_points = []

        for p in points:
            referenced_id = None
            if "Пригласил" in p.get("for_this", "") or "Регистрация по ссылке" in p.get("for_this", ""):
                referenced_id = int(p["for_this"].split()[-1])
                
            # Получаем username по referenced_id, если он есть
            username = None
            if referenced_id:
                user_data = self.db.get_data(table="users", column="id", element=referenced_id)
                if user_data:
                    username = user_data[0].get("username")  # Предполагаем, что get_data возвращает список словарей
            
            photo_url = self.get_photo_url_by_id(referenced_id) if referenced_id else None
            enriched_points.append({
                **p,
                "referenced_id": referenced_id,
                "username": username,
                "photo_url": photo_url
            })
        
        return jsonify({"data": enriched_points})


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

    def show_menu(self, message):
        referrer_id = None
        if message.text.startswith('/start '):
            payload = message.text.split(' ')[1]
            if payload.isdigit():
                referrer_id = int(payload)

        user_id = message.from_user.id
        username = message.from_user.username or "Без_ника"
        response = self.db.get_data(table="users", column="id", element=user_id)
        photos = self.bot.get_user_profile_photos(user_id)
        photo_url = None
        if photos.total_count > 0:
            file_id = photos.photos[0][0].file_id
            file_info = self.bot.get_file(file_id)
            photo_url = f"https://api.telegram.org/file/bot{self.bot.token}/{file_info.file_path}"

        if not response:
            self.db.insert_data(table="users", data={
                "id": user_id,
                "username": username,
                "referred_by": referrer_id,
                "photo_url": photo_url
            })

            referrer_user = self.db.get_data(table="users", column="id", element=referrer_id) 
            referrer_username = ( referrer_user[0].get("username") if referrer_user and isinstance(referrer_user, list) else "Неизвестно" )

            now = datetime.now().strftime("%d.%m.%Y %H:%M")

            # Добавляем поинты рефереру
            if referrer_id:
                self.db.insert_data(table="points", data={
                    "id": referrer_id,
                    "count": 150,
                    "for_this": f"Пригласил {user_id}",
                    "date": now
                })

            # Добавляем поинты новому пользователю
            self.db.insert_data(table="points", data={
                "id": user_id,
                "count": 150,
                "for_this": f"Регистрация по ссылке {referrer_id or 'нет'}",
                "date": now
            })
                # Приветственное сообщение
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

    def start_flask(self):
        debug = os.getenv("DEBUG", "False").lower() == "true"
        port = int(os.environ.get("PORT", 5000))
        self.app.run(port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    bot = Bot()
    flask_thread = threading.Thread(target=bot.start_flask)
    flask_thread.start()

    # Telegram-бот в основном потоке
    bot.bot.remove_webhook()
    bot.bot.infinity_polling(skip_pending=True)