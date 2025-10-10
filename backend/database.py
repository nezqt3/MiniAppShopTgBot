import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class DataBase(object):
    def __init__(self):
        self.url: str = os.environ.get("URL")
        self.key: str = os.environ.get("KEY")
        self.supabase: Client = create_client(self.url, self.key)
        
    def get_data(self, table: str = "users", column: str = "", element: str = "") -> list:
        response = self.supabase.table(table).select("*").eq(column, element).execute()
        return response.data
    
    def insert_data(self, table: str = "purchases", data: dict = {}) -> list:
        response = (
            self.supabase.table(table)
            .insert(data)
            .execute()
        )
        return response.data
    
    def update_data(self, table: str, match_column: str, match_value, data: dict) -> list:
        response = (
            self.supabase.table(table)
            .update(data)
            .eq(match_column, match_value)
            .execute()
        )
        return response.data