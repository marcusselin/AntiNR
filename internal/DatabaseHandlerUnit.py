import sqlite3
from typing import Optional
import os
from dotenv import load_dotenv
load_dotenv()

path = str(os.getenv("DATABASEPATH"))
if not path:
    print(":[")

class DatabaseHandler:
    #Initialize
    def __init__(self, db_path: str = path):
        if db_path is None:
            db_path = os.getenv("DATABASEPATH")
        self.db_path = db_path
        self._init_db()
    
    #Connect to database
    def _connect(self):
        return sqlite3.connect(self.db_path)

    #Initialize
    def _init_db(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guild_config (
                    guild_id INTEGER PRIMARY KEY,
                    report_channel_id INTEGER,
                    admin_role_id INTEGER
                )
            """)
            conn.commit()
    
    #Set report channel
    def set_report_channel(self, guild_id: int, channel_id: int):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO guild_config (guild_id, report_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET report_channel_id = excluded.report_channel_id
            """, (guild_id, channel_id))
            conn.commit()
    
    #Get report channel
    def get_report_channel(self, guild_id: int) -> Optional[int]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT report_channel_id FROM guild_config WHERE guild_id = ?
            """, (guild_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        
    #---------------------------------------------------------------------------------------------------------
    #Set admin role id
    def set_admin_role(self, guild_id: int, role_id: int):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO guild_config (guild_id, admin_role_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET admin_role_id = excluded.report_channel_id
            """, (guild_id, role_id))
            conn.commit()
    
    #Get admin role id
    def get_admin_role(self, guild_id: int) -> Optional[int]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT admin_role_id FROM guild_config WHERE guild_id = ?
            """, (guild_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    #---------------------------------------------------------------------------------------------------------
    #Check if bot is configurated (is there data of this server in database)
    def is_configured(self, guild_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""SELECT 1 FROM guild_config WHERE guild_id = ?""", (guild_id,))
            result = cursor.fetchone()
            return result is not None