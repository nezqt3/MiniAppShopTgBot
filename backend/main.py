from telebot import TeleBot, types
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from database import DataBase
import os
import hmac
import hashlib
import json
from datetime import datetime
import requests

load_dotenv(dotenv_path="/home/rupl/mysite/.env")
POINT_TO_CURRENCY = 1
MIN_POINTS_TO_REDEEM = 0

class Bot:
    def __init__(self):
        self.bot = TeleBot(token=os.getenv("TOKEN"), threaded=False)  # Важно: отключаем многопоточность
        self.db = DataBase()
        self.app = Flask(__name__)
        CORS(self.app, origins="*")

        # Устанавливаем webhook
        url = f"https://api.telegram.org/bot{os.getenv('TOKEN')}/setWebhook?url=https://rupl.pythonanywhere.com/bot"
        requests.get(url)

        self._register_handlers()
        self._register_apis()

    def _register_handlers(self):
        self.bot.register_message_handler(self.show_menu, commands=['start'])
        self.bot.register_message_handler(self.instructions, commands=['help'])
        self.bot.register_message_handler(self.add_purchase, commands=['send'])

    def _register_apis(self):
        self.app.route("/get_user", methods=['GET'])(self.get_user)
        self.app.route("/create_user", methods=['POST'])(self.create_user)
        self.app.route("/get_purchases", methods=['GET'])(self.get_purchases)
        self.app.route("/ping", methods=['GET'])(self.ping)
        self.app.route("/points/sum", methods=["GET"])(self.get_sum_points)
        self.app.route("/points/history", methods=["GET"])(self.get_history_points)
        self.app.route("/referral_link", methods=["PUT"])(self.put_referral_link)
        self.app.route("/bot", methods=["POST"])(self.webhook)

    # ----------------- Webhook -----------------
    def webhook(self):
        json_str = request.get_data().decode("utf-8")
        try:
            update = types.Update.de_json(json_str)
            self.bot.process_new_updates([update])  # обрабатываем прямо здесь
        except Exception as e:
            print("Ошибка обработки update:", e)
        return "ok", 200

    # ----------------- API -----------------
    def ping(self):
        return jsonify({"status": "ok", "message": "Flask API работает ✅"})

    def get_user_total_points(self, user_id):
        """Возвращает сумму баллов пользователя (считая отрицательные записи)."""
        points = self.db.get_data(table="points", column="id", element=user_id) or []
        return sum([p.get("count", 0) for p in points])

    def deduct_points_record(self, user_id, points_count, reason):
        """Добавляет запись в таблицу points с отрицательным значением (списание)."""
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.db.insert_data(table="points", data={
            "id": user_id,
            "count": -abs(int(points_count)),
            "for_this": reason,
            "date": now
        })

    def add_purchase(self, message):
        allowed_users = [6216832500, 1108856135]
        if message.from_user.id not in allowed_users:
            self.bot.send_message(message.chat.id, "❌ У вас нет прав на добавление покупки")
            return

        try:
            data = json.loads(message.text.replace("/send", "").strip())
        except json.JSONDecodeError:
            self.bot.send_message(message.chat.id, "❌ Ошибка: неверный формат данных")
            return

        user_id = data.get("id")
        name = data.get("name")
        amount = data.get("cost")
        count = data.get("count", 1)
        address = data.get("address")
        size = data.get("size")

        use_points = True if data.get("use_points", False) == "True" else False          # True/False
        points_to_use = int(data.get("points_to_use", 0))   # сколько баллов списать (int)

        if not user_id or not amount or amount <= 0:
            self.bot.send_message(message.chat.id, "❌ Ошибка: неверные данные (id или сумма)")
            return

        total_points = self.get_user_total_points(user_id)

        original_cost = float(amount)
        points_used = 0
        discount_amount = 0.0
        paid_cost = original_cost

        if use_points and points_to_use > 0:
            if points_to_use < MIN_POINTS_TO_REDEEM:
                self.bot.send_message(message.chat.id, f"❌ Можно списать минимум {MIN_POINTS_TO_REDEEM} баллов")
                return

            if points_to_use > total_points:
                self.bot.send_message(message.chat.id, "❌ У пользователя недостаточно баллов для списания")
                return

            discount_amount = points_to_use * self.POINT_TO_CURRENCY if hasattr(self, "POINT_TO_CURRENCY") else points_to_use * POINT_TO_CURRENCY
            if discount_amount >= original_cost:
                discount_amount = original_cost
                points_used = int(round(discount_amount / (self.POINT_TO_CURRENCY if hasattr(self, "POINT_TO_CURRENCY") else POINT_TO_CURRENCY)))
            else:
                points_used = points_to_use

            reason = f"Списание {points_used} баллов за покупку {original_cost}"
            try:
                self.deduct_points_record(user_id, points_used, reason)
            except Exception as e:
                self.bot.send_message(message.chat.id, f"❌ Ошибка при списании баллов: {e}")
                return

            paid_cost = round(original_cost - discount_amount, 2)

        if points_used == 0:
            user_points = round(original_cost * 0.03)
            now = datetime.now().strftime("%d.%m.%Y %H:%M")
            if user_points > 0:
                self.db.insert_data(table="points", data={
                    "id": user_id,
                    "count": user_points,
                    "for_this": f"Покупка на {original_cost}",
                    "date": now
                })


            user_data = self.db.get_data(table="users", column="id", element=user_id)
            if user_data and user_data[0].get("referred_by"):
                referrer_id = user_data[0]["referred_by"]
                referrer_points = round(original_cost * 0.01)
                if referrer_points > 0:
                    self.db.insert_data(table="points", data={
                        "id": referrer_id,
                        "count": referrer_points,
                        "for_this": f"Реферальная покупка пользователя {user_id} на {original_cost}",
                        "date": now
                    })
        else:
            pass

        # Сохраняем покупку с полями: original_cost, paid_cost, points_used, discount_amount
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.db.insert_data(table="purchases", data={
            "id": int(user_id),
            "cost": int(original_cost),
            "paid_cost": int(paid_cost),
            "count": int(count),
            "name": name,
            "address": address,
            "size": size,
            "date": now,
            "points_used": int(points_used),
            "discount_amount": int(discount_amount)
        })

        self.bot.send_message(message.chat.id, "✅ Данные покупки успешно добавлены")


    def get_user(self):
        user_id = request.args.get('id')
        user = self.db.get_data(column="id", element=user_id)
        return jsonify(user)

    def create_user(self):
        data = request.get_json()
        self.db.insert_data(table="users", data=data)
        return jsonify({"status": "success", "data": data})

    def get_purchases(self):
        user_id = request.args.get('id')
        data = self.db.get_data(table="purchases", column="id", element=user_id)
        return jsonify(data)

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
                try:
                    referenced_id = int(p["for_this"].split()[-1])
                except ValueError:
                    referenced_id = None

            username = None
            if referenced_id:
                user_data = self.db.get_data(table="users", column="id", element=referenced_id)
                if user_data:
                    username = user_data[0].get("username")

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

    # ----------------- Bot Handlers -----------------
    def show_menu(self, message):
        try:
            referrer_id = None
            if message.text.startswith('/start '):
                payload = message.text.split(' ')[1]
                if payload.isdigit():
                    referrer_id = int(payload)

            user_id = message.from_user.id
            username = message.from_user.username or "Без_ника"
            response = self.db.get_data(table="users", column="id", element=user_id)

            # Получаем фото пользователя
            photo_url = None
            photos = self.bot.get_user_profile_photos(user_id)
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

                now = datetime.now().strftime("%d.%m.%Y %H:%M")

                if referrer_id:
                    self.db.insert_data(table="points", data={
                        "id": referrer_id,
                        "count": 150,
                        "for_this": f"Пригласил {user_id}",
                        "date": now
                    })

                self.db.insert_data(table="points", data={
                    "id": user_id,
                    "count": 150,
                    "for_this": f"Регистрация по ссылке {referrer_id or 'нет'}",
                    "date": now
                })

            self.bot.send_message(
                message.chat.id,
                "👋 Привет!\n"
                "Тебя приветствует бот магазина Ghost404 🎁\n\n"
                "Вот что ты можешь сделать:\n"
                "• /start — вывести стартовое сообщение\n"
                "• /help — написать нашему менеджеру\n\n"
                "Также ты можешь открыть приложение, чтобы посмотреть всю информацию о своих баллах и рефералах.\n\n"
                "Вместе копить баллы — весело и выгодно! 🚀"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()

    def instructions(self, message):
        self.bot.send_message(
            message.chat.id,
            "💡 Краткие инструкции:\n"
            "1️⃣ Вся информация о ваших баллах и рефералах доступна только в приложении.\n"
            "2️⃣ Если вопросы — пишите менеджеру: @ghostedmng"
        )

    def start_flask(self):
        debug = os.getenv("DEBUG", "False").lower() == "true"
        port = int(os.environ.get("PORT", 5000))
        self.app.run(port=port, debug=debug, use_reloader=False)

# ----------------- Запуск -----------------
bot_instance = Bot()
app = bot_instance.app
