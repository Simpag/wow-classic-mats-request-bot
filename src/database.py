import sqlite3
import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from threading import Lock


@dataclass
class Item:
    id: Optional[int]
    guild_id: int
    name: str
    quantity: int
    description: Optional[str] = None


@dataclass
class ItemRequest:
    id: Optional[int]
    guild_id: int
    user_id: int
    user_name: str
    items: str  # JSON string of requested items
    status: str  # 'pending', 'approved', 'denied'
    created_at: str
    updated_at: Optional[str] = None


@dataclass
class GuildConfig:
    guild_id: int
    inventory_channel_id: Optional[int]
    inventory_message_id: Optional[int]
    admin_role_ids: str  # JSON string of role IDs


class Database:
    def __init__(self, db_path: str = "inventory.db"):
        self.db_path = db_path
        self.lock = Lock()
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_database(self):
        """Initialize the database with required tables."""
        with self.lock:
            with self.get_connection() as conn:
                # Create guild_configs table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS guild_configs (
                        guild_id INTEGER PRIMARY KEY,
                        inventory_channel_id INTEGER,
                        inventory_message_id INTEGER,
                        admin_role_ids TEXT DEFAULT '[]'
                    )
                """
                )

                # Create items table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        quantity INTEGER NOT NULL DEFAULT 0,
                        description TEXT,
                        UNIQUE(guild_id, name)
                    )
                """
                )

                # Create item_requests table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS item_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        user_name TEXT NOT NULL,
                        items TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                """
                )

                conn.commit()
                print("✅ Database tables initialized successfully")

    # Guild Config Methods
    def get_guild_config(self, guild_id: int) -> Optional[GuildConfig]:
        """Get guild configuration."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT guild_id, inventory_channel_id, inventory_message_id, admin_role_ids FROM guild_configs WHERE guild_id = ?",
                    (guild_id,),
                )
                row = cursor.fetchone()
                if row:
                    return GuildConfig(
                        guild_id=row[0],
                        inventory_channel_id=row[1],
                        inventory_message_id=row[2],
                        admin_role_ids=row[3],
                    )
                return None

    def set_guild_config(self, guild_id: int, **kwargs) -> None:
        """Set guild configuration."""
        with self.lock:
            with self.get_connection() as conn:
                # Check if config exists
                cursor = conn.execute(
                    "SELECT * FROM guild_configs WHERE guild_id = ?", (guild_id,)
                )
                exists = cursor.fetchone() is not None

                if exists:
                    # Update existing config
                    updates = []
                    params = []
                    if "inventory_channel_id" in kwargs:
                        updates.append("inventory_channel_id = ?")
                        params.append(kwargs["inventory_channel_id"])
                    if "inventory_message_id" in kwargs:
                        updates.append("inventory_message_id = ?")
                        params.append(kwargs["inventory_message_id"])
                    if "admin_role_ids" in kwargs:
                        updates.append("admin_role_ids = ?")
                        params.append(kwargs["admin_role_ids"])

                    if updates:
                        params.append(guild_id)
                        conn.execute(
                            f'UPDATE guild_configs SET {", ".join(updates)} WHERE guild_id = ?',
                            params,
                        )
                else:
                    # Create new config
                    conn.execute(
                        "INSERT INTO guild_configs (guild_id, inventory_channel_id, inventory_message_id, admin_role_ids) VALUES (?, ?, ?, ?)",
                        (
                            guild_id,
                            kwargs.get("inventory_channel_id"),
                            kwargs.get("inventory_message_id"),
                            kwargs.get("admin_role_ids", "[]"),
                        ),
                    )

                conn.commit()

    # Item Methods
    def get_items(self, guild_id: int) -> List[Item]:
        """Get all items for a guild."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, guild_id, name, quantity, description FROM items WHERE guild_id = ? ORDER BY name",
                (guild_id,),
            )
            return [
                Item(
                    id=row[0],
                    guild_id=row[1],
                    name=row[2],
                    quantity=row[3],
                    description=row[4],
                )
                for row in cursor.fetchall()
            ]

    def get_item(self, guild_id: int, name: str) -> Optional[Item]:
        """Get a specific item by name."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, guild_id, name, quantity, description FROM items WHERE guild_id = ? AND name = ?",
                (guild_id, name),
            )
            row = cursor.fetchone()
            if row:
                return Item(
                    id=row[0],
                    guild_id=row[1],
                    name=row[2],
                    quantity=row[3],
                    description=row[4],
                )
            return None

    def add_item(
        self, guild_id: int, name: str, quantity: int = 0, description: str = None
    ) -> bool:
        """Add a new item to the inventory."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO items (guild_id, name, quantity, description) VALUES (?, ?, ?, ?)",
                    (guild_id, name, quantity, description),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Item already exists

    def update_item_quantity(self, guild_id: int, name: str, quantity: int) -> bool:
        """Update item quantity."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE items SET quantity = ? WHERE guild_id = ? AND name = ?",
                (quantity, guild_id, name),
            )
            conn.commit()
            return cursor.rowcount > 0

    def add_item_quantity(self, guild_id: int, name: str, quantity: int) -> bool:
        """Add to item quantity."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE items SET quantity = quantity + ? WHERE guild_id = ? AND name = ?",
                (quantity, guild_id, name),
            )
            conn.commit()
            return cursor.rowcount > 0

    def remove_item_quantity(self, guild_id: int, name: str, quantity: int) -> bool:
        """Remove from item quantity (won't go below 0)."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE items SET quantity = MAX(0, quantity - ?) WHERE guild_id = ? AND name = ?",
                (quantity, guild_id, name),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_item(self, guild_id: int, name: str) -> bool:
        """Delete an item from inventory."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM items WHERE guild_id = ? AND name = ?", (guild_id, name)
            )
            conn.commit()
            return cursor.rowcount > 0

    # Request Methods
    def create_request(
        self, guild_id: int, user_id: int, user_name: str, items: str
    ) -> int:
        """Create a new item request."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO item_requests (guild_id, user_id, user_name, items) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, user_name, items),
            )
            conn.commit()
            return cursor.lastrowid

    def get_requests(self, guild_id: int, status: str = None) -> List[ItemRequest]:
        """Get requests for a guild, optionally filtered by status."""
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute(
                    """SELECT id, guild_id, user_id, user_name, items, status, created_at, updated_at 
                       FROM item_requests WHERE guild_id = ? AND status = ? ORDER BY created_at""",
                    (guild_id, status),
                )
            else:
                cursor = conn.execute(
                    """SELECT id, guild_id, user_id, user_name, items, status, created_at, updated_at 
                       FROM item_requests WHERE guild_id = ? ORDER BY created_at""",
                    (guild_id,),
                )

            return [
                ItemRequest(
                    id=row[0],
                    guild_id=row[1],
                    user_id=row[2],
                    user_name=row[3],
                    items=row[4],
                    status=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                )
                for row in cursor.fetchall()
            ]

    def update_request_status(self, request_id: int, status: str) -> bool:
        """Update request status."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE item_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, request_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_request(self, request_id: int) -> Optional[ItemRequest]:
        """Get a specific request by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT id, guild_id, user_id, user_name, items, status, created_at, updated_at 
                   FROM item_requests WHERE id = ?""",
                (request_id,),
            )
            row = cursor.fetchone()
            if row:
                return ItemRequest(
                    id=row[0],
                    guild_id=row[1],
                    user_id=row[2],
                    user_name=row[3],
                    items=row[4],
                    status=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                )
            return None
