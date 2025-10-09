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
        self.bot.register_message_handler(self.handle_start , commands=['start'])
        self.bot.register_callback_query_handler(self.show_user_profile, func=lambda callback: callback.data == 'user')
        self.bot.register_callback_query_handler(self.referal_url, func=lambda callback: callback.data == 'referal')
        
    def _register_apis(self):
        self.app.route("/last_users", methods=['GET'])(self.get_last_user)
        
    def get_last_user(self):
        if last_users:
            return jsonify(last_users[-1])
        return jsonify({})
        
    def handle_start(self, message):
        args = message.text.split()
        user_id = message.from_user.id
        username = message.from_user.username
        
        last_users.append({"user_id": user_id, "username": username})
        self.bot.send_message(message.chat.id, "qe123")
        
        if user_id not in points:
            self.points[user_id] = 0
        
        if len(args) > 1:
            referrer_id = int(args[1])
            if referrer_id != user_id:
                points[referrer_id] = points.get(referrer_id, 0) + 50
                print(f"Пользователь {user_id} пришел по реферальной ссылке {referrer_id}. Баллы {referrer_id} = {points[referrer_id]}")
        
        self.show_menu(message)
        
    def show_menu(self, message):
        keyboard = types.InlineKeyboardMarkup()
        button_about_user = types.InlineKeyboardButton(text="Профиль", callback_data="user")
        button_referal = types.InlineKeyboardButton(text="Реферальная ссылка", callback_data="referal")
        
        keyboard.add(button_about_user, button_referal, row_width=1)
        self.bot.send_message(
            message.chat.id,
            text=(
                "👋 Привет!\n\n"
                "Тебя приветствует бот магазина **SuperShop** 🎁\n\n"
                "Здесь ты можешь:\n"
                "💰 Посмотреть, сколько бонусных баллов ты уже накопил\n"
                "🤝 Создать собственную *реферальную ссылку* и поделиться ею с друзьями\n\n"
                "Вместе копить баллы веселее и выгоднее! 🚀",
            ),
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    def show_user_profile(self, callback):
        user_id = callback.from_user.id
        username = callback.from_user.first_name or "Пользователь"
        points = 125
        
        text = (
            f"👤 *Профиль пользователя*\n\n"
            f"Имя: {username}\n"
            f"ID: `{user_id}`\n"
            f"💎 Баллы: <b>{points}</b>\n\n"
            f"Продолжай приглашать друзей и делай покупи, чтобы увеличивать свой баланс! 🚀"
        )
        
        self.bot.send_message(callback.message.chat.id, text, parse_mode="HTML")
        
    def referal_url(self, callback):
        user_id = callback.from_user.id
        
        if user_id not in referrals:
            base_url = "https://t.me/referalApi_bot?start="
            encoded_ref = urllib.parse.quote_plus(str(user_id))
            referral_link = f"{base_url}{encoded_ref}"
            referrals[user_id] = referral_link
        else:
            referral_link = referrals[user_id]
        
        text = (
            "🔗 <b>Твоя реферальная ссылка</b>\n\n"
            "Отправь её друзьям — и получай бонусы, когда они присоединятся и будут делать покупки!\n\n"
            f"👉 <a href='#'>{referral_link}</a>"
        )
        
        print(referral_link, user_id)
        self.bot.send_message(callback.message.chat.id, text, parse_mode="HTML")
        
    def start_bot(self):
        self.bot.infinity_polling()
        

if __name__ == "__main__":
    import threading
    bot = Bot()
    threading.Thread(target=bot.start_bot).start()