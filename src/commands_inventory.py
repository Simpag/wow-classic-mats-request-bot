import json
import discord
from discord import Interaction, app_commands
from discord.ext import commands
from datetime import datetime

# Import from local modules
try:
    from .database import Database
    from .inventory_manager import InventoryManager, RequestView
except ImportError:
    from database import Database
    from inventory_manager import InventoryManager, RequestView


class InventoryCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database):
        self.bot = bot
        self.db = database
        self.inventory = InventoryManager(bot, database)

    # User Commands
    # @app_commands.command(
    #     name="inventory", description="View the current guild inventory"
    # )
    # async def view_inventory(self, interaction: Interaction):
    #     """Display the current inventory."""
    #     embed = self.inventory.create_inventory_embed(interaction.guild.id)
    #     await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="request", description="Request items from the guild inventory"
    )
    @app_commands.describe(
        items="Items to request (format: 'Iron Ore: 50, Copper Ore: 100' or 'Iron Ore 50, Copper Ore 100')"
    )
    async def request_items(self, interaction: Interaction, items: str):
        """Request items from the inventory."""
        # Parse the items
        try:
            requested_items = self.inventory.parse_item_input(items)
        except Exception as e:
            await interaction.response.send_message(
                "❌ Invalid item format. Please use format like: `Iron Ore: 50, Copper Ore: 100`",
                ephemeral=True,
            )
            return

        if not requested_items:
            await interaction.response.send_message(
                "❌ No valid items found. Please use format like: `Iron Ore: 50, Copper Ore: 100`",
                ephemeral=True,
            )
            return

        # Check if requested items exist in inventory
        guild_items = self.db.get_items(interaction.guild.id)
        guild_item_names = {item.name.lower(): item.name for item in guild_items}

        validated_items = {}
        invalid_items = []

        for item_name, quantity in requested_items.items():
            # Case-insensitive search
            lower_name = item_name.lower()
            if lower_name in guild_item_names:
                validated_items[guild_item_names[lower_name]] = quantity
            else:
                invalid_items.append(item_name)

        # Get inventory channel from config
        guild_config = self.db.get_guild_config(interaction.guild.id)
        if not guild_config or not guild_config.inventory_channel_id:
            await interaction.response.send_message(
                "❌ Inventory channel not set. Please contact an admin to set it up.",
                ephemeral=True,
            )
            return

        inventory_channel = self.bot.get_channel(guild_config.inventory_channel_id)

        if invalid_items:
            if inventory_channel != interaction.channel:
                await interaction.response.send_message(
                    f"❌ The following items are not in the inventory: {', '.join(invalid_items)}\n"
                    f"See available items in {inventory_channel.mention}.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"❌ The following items are not in the inventory: {', '.join(invalid_items)}\n"
                    f"See available items above.",
                    ephemeral=True,
                )
            return

        if not validated_items:
            await interaction.response.send_message(
                f"❌ No valid items found in inventory. See available items in {inventory_channel.mention}.",
                ephemeral=True,
            )
            return

        # Create the request
        request_id = self.db.create_request(
            interaction.guild.id,
            interaction.user.id,
            interaction.user.display_name,
            json.dumps(validated_items),
        )

        # Get the created request for the public announcement
        request = self.db.get_request(request_id)

        # Create public embed for the request
        public_embed = self.inventory.create_public_request_embed(
            request, interaction.user
        )

        # Create the view with approve/deny buttons
        view = RequestView(self.bot, self.db, self.inventory, request_id)

        # Post the public request announcement
        try:
            await inventory_channel.send(
                content=f"📢 **New Guild Item Request**\n{interaction.user.mention} has requested items from the guild inventory:",
                embed=public_embed,
                view=view,
            )

            # Respond to the user with confirmation
            if inventory_channel != interaction.channel:
                await interaction.response.send_message(
                    f"✅ Your request has been posted in {inventory_channel.mention} for admin review!",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "✅ Your request has been posted for admin review!", ephemeral=True
                )

        except discord.Forbidden:
            # Bot doesn't have permissions in inventory channel, post in current channel
            await interaction.response.send_message(
                content=f"📢 **New Guild Item Request**\n{interaction.user.mention} has requested items from the guild inventory (bot denied access to: {inventory_channel.mention}):",
                embed=public_embed,
                view=view,
            )

        # Send a confirmation DM to the user
        try:
            confirmation_embed = discord.Embed(
                title="📋 Request Submitted",
                description=f"Your request has been submitted and posted for admin review.",
                color=discord.Color.blue(),
            )

            items_text = []
            for item_name, quantity in validated_items.items():
                items_text.append(f"**{item_name}**: {quantity:,}")

            confirmation_embed.add_field(
                name="Requested Items", value="\n".join(items_text), inline=False
            )
            confirmation_embed.add_field(
                name="Server", value=interaction.guild.name, inline=True
            )
            confirmation_embed.add_field(
                name="Request ID", value=f"#{request_id}", inline=True
            )
            confirmation_embed.add_field(name="Status", value="Pending", inline=True)

            await interaction.user.send(embed=confirmation_embed)
        except:
            # User might have DMs disabled, which is fine
            pass

    @app_commands.command(
        name="my_requests", description="View your pending item requests"
    )
    async def my_requests(self, interaction: Interaction):
        """Show the user's requests."""
        requests = self.db.get_requests(interaction.guild.id)
        user_requests = [req for req in requests if req.user_id == interaction.user.id]

        if not user_requests:
            await interaction.response.send_message(
                "📭 You have no item requests.", ephemeral=True
            )
            return

        embed = discord.Embed(title="📋 Your Item Requests", color=discord.Color.blue())

        print(f"Found {len(user_requests)} requests for user {interaction.user.id}")

        for request in user_requests[-10:]:  # Show last 10 requests
            requested_items = json.loads(request.items)
            items_text = ", ".join(
                [f"{name}: {qty}" for name, qty in requested_items.items()]
            )

            status_emoji = {"pending": "🟡", "approved": "🟢", "denied": "🔴"}.get(
                request.status, "⚪"
            )

            embed.add_field(
                name=f"{status_emoji} Request #{request.id} - {request.status.capitalize()}",
                value=f"{items_text}\nCreated: {datetime.fromisoformat(request.created_at).strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)
