import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class DataBase(object):
    def __init__(self):
        self.url: str = os.environ.get("URL")
        self.key: str = os.environ.get("KEY")
        self.supabase: Client = create_client(self.url, self.key)
        
    def get_data(self, table: str = "purchases", column: str = "*") -> dict:
        response = self.supabase.table(table).select(column).execute()
        return response.data
    
    def insert_data(self, table: str = "purchases", data: dict = {}) -> list:
        response = (
            self.supabase.table(table)
            .insert(data)
            .execute()
        )
        return response.data

        
db = DataBase()

print(db.insert_data("users", {"id": 312311, "username": "nezqt3", "photo_url": ""}))
print(db.get_data())
