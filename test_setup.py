#!/usr/bin/env python3
"""
Test script to validate bot setup without actually starting the Discord bot
"""

import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    print("🔍 Testing imports...")

    from database import Database

    print("✅ Database module imported successfully")

    from inventory_manager import InventoryManager

    print("✅ InventoryManager module imported successfully")

    from commands import InventoryCommands, AdminCommands

    print("✅ Commands modules imported successfully")

    print("\n🗄️ Testing database initialization...")
    import tempfile
    import os

    # Create a temporary database file for testing
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()

    try:
        db = Database(temp_db.name)
        print("✅ Database initialized successfully")

        print("\n🧪 Testing database operations...")
        # Test simple guild config
        db.set_guild_config(123456789, inventory_channel_id=987654321)
        print("✅ Guild config set successfully")

        config = db.get_guild_config(123456789)
        if config and config.inventory_channel_id == 987654321:
            print("✅ Guild config retrieval works")
        else:
            print(f"❌ Config retrieval failed: {config}")
            raise AssertionError("Guild config test failed")

        # Test adding an item
        success = db.add_item(123456789, "Iron Ore", 100, "Used for blacksmithing")
        if success:
            print("✅ Item addition works")
        else:
            print("❌ Item addition failed")
            raise AssertionError("Item addition failed")

        items = db.get_items(123456789)
        if len(items) == 1 and items[0].name == "Iron Ore" and items[0].quantity == 100:
            print("✅ Item retrieval works")
        else:
            print(f"❌ Item retrieval failed: {items}")
            raise AssertionError("Item retrieval failed")

        # Test creating a request
        request_id = db.create_request(
            123456789, 456789123, "TestUser", '{"Iron Ore": 50}'
        )
        if request_id:
            print("✅ Request creation works")
        else:
            print("❌ Request creation failed")
            raise AssertionError("Request creation failed")

        requests = db.get_requests(123456789)
        if len(requests) == 1 and requests[0].user_name == "TestUser":
            print("✅ Request retrieval works")
        else:
            print(f"❌ Request retrieval failed: {requests}")
            raise AssertionError("Request retrieval failed")

    finally:
        # Clean up the temporary database file
        try:
            os.unlink(temp_db.name)
        except:
            pass

    print("\n🎉 All tests passed! Your bot setup is ready.")
    print("\n📋 Next steps:")
    print("1. Create a .env file with your DISCORD_TOKEN")
    print("2. Update the GUILD_ID in run.py with your Discord server ID")
    print("3. Run the bot with: python run.py")
    print(
        "\n💡 Tip: Make sure your bot has the necessary permissions in your Discord server!"
    )

except ImportError as e:
    print(f"❌ Import error: {e}")
    print(
        "Make sure you've installed the requirements: pip install -r requirements.txt"
    )
    sys.exit(1)

except AssertionError as e:
    print(f"❌ Database test failed: {e}")
    sys.exit(1)

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
