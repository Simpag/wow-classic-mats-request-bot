import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from local modules
from src.database import Database
from src.commands_inventory import InventoryCommands
from src.commands_admin import AdminCommands
from src.commands_owner import OwnerCommands
from src.inventory_manager import InventoryManager, PersistentRequestView

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
COMMAND_PREFIX = "!"  # Default command prefix
SHOULD_SYNC = False  # Disabled automatic syncing - use manual sync command instead
GUILD_ID = 1402810501058134151  # Your test server ID
OWNER_ID = 123106863066775552  # Your Discord ID for admin commands


class GuildBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents)

        # Database setup
        self.database = Database()

        # Inventory manager setup
        self.inventory_manager = InventoryManager(self, self.database)

        # Add persistent view for request buttons
        self.persistent_view = PersistentRequestView()
        self.add_view(self.persistent_view)

    async def setup_hook(self):
        """Setup the bot when it starts."""
        print("Bot setup starting...")

        # Initialize database
        print("Step 1: Initializing database...")
        # Database is auto-initialized in __init__, just confirm it's ready
        print("✓ Database initialized successfully")

        # Add cogs
        print("Step 2: Adding command cogs...")
        await self.add_cog(InventoryCommands(self, self.database))

        # Add admin commands cog - this will contain the admin group
        admin_cog = AdminCommands(self, self.database)
        await self.add_cog(admin_cog)

        # Add the admin group to the command tree
        self.tree.add_command(admin_cog.admin)

        await self.add_cog(OwnerCommands(self, GUILD_ID, OWNER_ID))
        print("✓ Command cogs added successfully")

        # Set up persistent view dependencies after bot is ready
        print("Step 3: Setting up persistent views...")
        self.persistent_view.set_dependencies(
            self, self.database, self.inventory_manager
        )
        print("✓ Persistent views configured")

        # Debug: Check what commands are in the tree
        print("Commands in tree:")
        for cmd in self.tree.walk_commands():
            print(f"  /{cmd.name} (type: {type(cmd).__name__})")
        for cmd in self.walk_commands():
            print(f"  {COMMAND_PREFIX}{cmd.name} (type: {type(cmd).__name__})")

        print("✅ Bot setup complete!")

    async def on_ready(self):
        """Called when the bot is ready."""
        print(f"Step 4: {self.user} has connected to Discord!")

        # Print guild information
        for guild in self.guilds:
            print(f"Connected to guild: {guild.name} (id: {guild.id})")

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild."""
        print(f"Joined new guild: {guild.name} (id: {guild.id})")

        # Only sync to our test server during development
        if SHOULD_SYNC and guild.id == GUILD_ID:
            try:
                guild_obj = discord.Object(id=guild.id)
                synced = await self.tree.sync(guild=guild_obj)
                print(f"Synced {len(synced)} commands to {guild.name}")
            except Exception as e:
                print(f"Failed to sync commands to {guild.name}: {e}")


async def main():
    """Main function to run the bot."""
    if not TOKEN:
        print("❌ DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token:")
        print("DISCORD_TOKEN=your_token_here")
        return

    bot = GuildBot()

    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
