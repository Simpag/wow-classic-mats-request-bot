import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from local modules
from src.database import Database
from src.commands import InventoryCommands, AdminCommands
from src.timezone_utils import set_wow_region, get_wow_region_info, set_guild_wow_region

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
SHOULD_SYNC = os.getenv("SHOULD_SYNC", "true").lower() == "true"
GUILD_ID = 1402810501058134151  # Your test server ID
WOW_REGION = os.getenv("WOW_REGION", "US")  # Default to US servers


class GuildBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        # Database setup
        self.db = Database()
        
        # Configure WoW server timezone
        set_wow_region(WOW_REGION)
        region_info = get_wow_region_info()
        print(f"🌍 Default WoW Region: {region_info['region']} ({region_info['timezone']})")
        print(f"🕒 Current WoW Time: {region_info['current_time']}")
         # Load guild-specific timezones from database
        self._load_guild_timezones()

    def _load_guild_timezones(self):
        """Load guild-specific WoW timezones from database."""
        try:
            # Get all guild configs and set their timezones
            with self.db.get_connection() as conn:
                cursor = conn.execute("SELECT guild_id, wow_region FROM guild_configs WHERE wow_region IS NOT NULL")
                for row in cursor.fetchall():
                    guild_id, wow_region = row
                    set_guild_wow_region(guild_id, wow_region)
                    print(f"  └── Guild {guild_id}: {wow_region} timezone")
        except Exception as e:
            print(f"Warning: Could not load guild timezones: {e}")
    
    async def setup_hook(self):
        """Setup the bot when it starts."""
        print("Bot setup starting...")

        # Initialize database
        print("Step 1: Initializing database...")
        # Database is auto-initialized in __init__, just confirm it's ready
        print("✓ Database initialized successfully")

        # Add cogs
        print("Step 2: Adding command cogs...")
        await self.add_cog(InventoryCommands(self, self.db))

        # Add admin commands cog - this will contain the admin group
        admin_cog = AdminCommands(self, self.db)
        await self.add_cog(admin_cog)

        # Add the admin group to the command tree
        self.tree.add_command(admin_cog.admin)
        print("✓ Command cogs added successfully")

        # Debug: Check what commands are in the tree
        print("Commands in tree:")
        for cmd in self.tree.get_commands():
            print(f"  - {cmd.name} (type: {type(cmd).__name__})")

        # Sync commands
        if SHOULD_SYNC:
            print("Step 3: Syncing commands to Discord...")
            try:
                # Global sync works more reliably than guild-specific sync
                # Commands will be available globally but bot is only in your test server
                guild_obj = discord.Object(id=GUILD_ID)
                synced = await self.tree.sync(guild=guild_obj)
                # synced = await self.tree.sync()
                print(f"✓ Synced {len(synced)} commands globally")
                for cmd in synced:
                    print(f"  - {cmd.name}")
            except Exception as e:
                print(f"❌ Failed to sync commands: {e}")
        else:
            print("Step 3: Command syncing disabled")

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
