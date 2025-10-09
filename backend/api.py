from flask import Flask, request, jsonify
from flask_cors import CORS

class Api(object):
    def __init__(self):
        self.app = Flask()
        CORS(self.app)
        self.last_users = []
        
        self._register_apis()
        self.app.run(port=5000)
        
    def _register_apis(self):
        self.app.route("/last_users", method='GET') (self.get_last_user)
        
    def get_last_user(self):
        return jsonify(self.last_users[-1])