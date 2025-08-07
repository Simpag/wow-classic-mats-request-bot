import json
import discord
from discord import Interaction, app_commands
from discord.ext import commands
from typing import Optional, List
from datetime import datetime

# Import from local modules
try:
    from .database import Database
    from .inventory_manager import InventoryManager, RequestView
    from .timezone_utils import (
        format_for_discord,
        get_wow_time,
        set_guild_wow_region,
        get_available_regions,
    )
except ImportError:
    from database import Database
    from inventory_manager import InventoryManager, RequestView
    from timezone_utils import (
        format_for_discord,
        get_wow_time,
        set_guild_wow_region,
        get_available_regions,
    )


class InventoryCommands(commands.Cog):
    def __init__(self, bot, database: Database):
        self.bot = bot
        self.db = database
        self.inventory = InventoryManager(bot, database)

    # User Commands
    @app_commands.command(
        name="inventory", description="View the current guild inventory"
    )
    async def view_inventory(self, interaction: Interaction):
        """Display the current inventory."""
        embed = self.inventory.create_inventory_embed(interaction.guild.id)
        await interaction.response.send_message(embed=embed)

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

        if invalid_items:
            await interaction.response.send_message(
                f"❌ The following items are not in the inventory: {', '.join(invalid_items)}\n"
                f"Use `/inventory` to see available items.",
                ephemeral=True,
            )
            return

        if not validated_items:
            await interaction.response.send_message(
                "❌ No valid items found in inventory. Use `/inventory` to see available items.",
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

        # Try to post in the inventory channel, otherwise post in current channel
        config = self.db.get_guild_config(interaction.guild.id)
        target_channel = None

        if config and config.inventory_channel_id:
            target_channel = self.bot.get_channel(config.inventory_channel_id)

        if not target_channel:
            target_channel = interaction.channel

        # Post the public request announcement
        try:
            await target_channel.send(
                content=f"📢 **New Guild Item Request**\n{interaction.user.mention} has requested items from the guild inventory:",
                embed=public_embed,
                view=view,
            )

            # Respond to the user with confirmation
            if target_channel != interaction.channel:
                await interaction.response.send_message(
                    f"✅ Your request has been posted in {target_channel.mention} for admin review!",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "✅ Your request has been posted for admin review!", ephemeral=True
                )

        except discord.Forbidden:
            # Bot doesn't have permissions in inventory channel, post in current channel
            await interaction.response.send_message(
                content=f"📢 **New Guild Item Request**\n{interaction.user.mention} has requested items from the guild inventory:",
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
                name="Request ID", value=f"#{request_id}", inline=True
            )
            confirmation_embed.add_field(name="Status", value="Pending", inline=True)
            confirmation_embed.set_footer(text=f"Server: {interaction.guild.name}")

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

        for request in user_requests[-10]:  # Show last 10 requests
            requested_items = json.loads(request.items)
            items_text = ", ".join(
                [f"{name} ({qty})" for name, qty in requested_items.items()]
            )

            status_emoji = {"pending": "🟡", "approved": "🟢", "denied": "🔴"}.get(
                request.status, "⚪"
            )

            embed.add_field(
                name=f"{status_emoji} Request #{request.id} - {request.status.capitalize()}",
                value=f"{items_text}\nCreated: {format_for_discord(datetime.fromisoformat(request.created_at), guild_id=interaction.guild.id)}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


# Admin Commands Group
class AdminCommands(commands.Cog):
    def __init__(self, bot, database: Database):
        self.bot = bot
        self.db = database
        self.inventory = InventoryManager(bot, database)

        # Create admin group
        self.admin = app_commands.Group(
            name="admin", description="Admin commands for inventory management"
        )

        # Add commands to group
        self.admin.command(
            name="setup", description="Setup the inventory system for this server"
        )(self.setup)
        self.admin.command(
            name="add_item", description="Add a new item to the inventory"
        )(self.add_item)
        self.admin.command(
            name="set_quantity", description="Set the quantity of an item"
        )(self.set_quantity)
        self.admin.command(
            name="add_quantity", description="Add to the quantity of an item"
        )(self.add_quantity)
        self.admin.command(
            name="remove_item", description="Remove an item from the inventory"
        )(self.remove_item)
        self.admin.command(name="requests", description="View pending item requests")(
            self.view_requests
        )
        self.admin.command(
            name="manual_approve", description="Manually approve a request by ID"
        )(self.manual_approve_request)

    def is_inventory_admin(self, interaction: Interaction) -> bool:
        """Check if user can manage inventory."""
        return self.inventory.is_admin(interaction.user, interaction.guild.id)

    # Admin command methods
    @app_commands.describe(
        channel="Channel where the inventory will be displayed",
        admin_roles="Comma-separated list of roles that can manage inventory (optional)",
        timezone="WoW server timezone (US=Pacific, EU=Central European, OCE=Australian Eastern)",
    )
    @app_commands.choices(
        timezone=[
            app_commands.Choice(name="US - Pacific Time (PST/PDT)", value="US"),
            app_commands.Choice(
                name="EU - Central European Time (CET/CEST)", value="EU"
            ),
            app_commands.Choice(
                name="OCE - Australian Eastern Time (AEST/AEDT)", value="OCE"
            ),
        ]
    )
    async def setup(
        self,
        interaction: Interaction,
        channel: discord.TextChannel,
        admin_roles: Optional[str] = None,
        timezone: Optional[str] = "US",
    ):
        """Setup the inventory system."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need Administrator permissions to setup the inventory system.",
                ephemeral=True,
            )
            return

        guild_id = interaction.guild.id

        # Parse admin roles if provided
        admin_role_ids = []
        if admin_roles:
            role_names = [name.strip() for name in admin_roles.split(",")]
            for role_name in role_names:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    admin_role_ids.append(role.id)

        # Update guild config
        self.db.set_guild_config(
            guild_id,
            inventory_channel_id=channel.id,
            admin_role_ids=json.dumps(admin_role_ids),
            wow_region=timezone,
        )

        # Set the timezone for this guild
        set_guild_wow_region(guild_id, timezone)

        # Create initial inventory display
        success = await self.inventory.update_inventory_display(guild_id)

        embed = discord.Embed(
            title="✅ Setup Complete",
            description=f"Inventory system has been configured for this server.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Inventory Channel", value=channel.mention, inline=False)

        if admin_role_ids:
            role_mentions = [f"<@&{role_id}>" for role_id in admin_role_ids]
            embed.add_field(
                name="Admin Roles", value=", ".join(role_mentions), inline=False
            )
        else:
            embed.add_field(
                name="Admin Roles", value="Server Administrators only", inline=False
            )

        # Show timezone info
        timezone_names = {
            "US": "US - Pacific Time (PST/PDT)",
            "EU": "EU - Central European Time (CET/CEST)",
            "OCE": "OCE - Australian Eastern Time (AEST/AEDT)",
        }
        embed.add_field(
            name="WoW Server Timezone",
            value=timezone_names.get(timezone, f"{timezone} timezone"),
            inline=False,
        )

        embed.add_field(
            name="Next Steps",
            value="• Use `/admin add_item` to add items to inventory\n• Users can use `/request` to request items\n• Use `/admin` commands to manage requests",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

        if success:
            await channel.send(
                "🏛️ **Guild Inventory System Activated**\nThis message will automatically update to show current inventory levels."
            )

    @app_commands.describe(
        name="Name of the item",
        quantity="Initial quantity (default: 0)",
        description="Optional description of the item",
    )
    async def add_item(
        self,
        interaction: Interaction,
        name: str,
        quantity: int = 0,
        description: Optional[str] = None,
    ):
        """Add a new item to the inventory."""
        if not self.is_inventory_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to manage inventory.", ephemeral=True
            )
            return

        success = self.db.add_item(interaction.guild.id, name, quantity, description)

        if success:
            embed = discord.Embed(
                title="✅ Item Added",
                description=f"**{name}** has been added to the inventory.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Quantity", value=f"{quantity:,}", inline=True)
            if description:
                embed.add_field(name="Description", value=description, inline=True)

            await interaction.response.send_message(embed=embed)
            await self.inventory.update_inventory_display(interaction.guild.id)
        else:
            await interaction.response.send_message(
                f"❌ Item **{name}** already exists in inventory.", ephemeral=True
            )

    @app_commands.describe(name="Name of the item", quantity="New quantity")
    async def set_quantity(self, interaction: Interaction, name: str, quantity: int):
        """Set the quantity of an item."""
        if not self.is_inventory_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to manage inventory.", ephemeral=True
            )
            return

        # Check if item exists
        item = self.db.get_item(interaction.guild.id, name)
        if not item:
            await interaction.response.send_message(
                f"❌ Item **{name}** not found in inventory.", ephemeral=True
            )
            return

        old_quantity = item.quantity
        success = self.db.update_item_quantity(interaction.guild.id, name, quantity)

        if success:
            embed = discord.Embed(
                title="✅ Quantity Updated",
                description=f"**{name}** quantity updated.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Old Quantity", value=f"{old_quantity:,}", inline=True)
            embed.add_field(name="New Quantity", value=f"{quantity:,}", inline=True)

            await interaction.response.send_message(embed=embed)
            await self.inventory.update_inventory_display(interaction.guild.id)
        else:
            await interaction.response.send_message(
                f"❌ Failed to update quantity for **{name}**.", ephemeral=True
            )

    @app_commands.describe(name="Name of the item", quantity="Amount to add")
    async def add_quantity(self, interaction: Interaction, name: str, quantity: int):
        """Add to the quantity of an item."""
        if not self.is_inventory_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to manage inventory.", ephemeral=True
            )
            return

        # Check if item exists
        item = self.db.get_item(interaction.guild.id, name)
        if not item:
            await interaction.response.send_message(
                f"❌ Item **{name}** not found in inventory.", ephemeral=True
            )
            return

        old_quantity = item.quantity
        success = self.db.add_item_quantity(interaction.guild.id, name, quantity)

        if success:
            embed = discord.Embed(
                title="✅ Quantity Added",
                description=f"Added {quantity:,} **{name}** to inventory.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Previous", value=f"{old_quantity:,}", inline=True)
            embed.add_field(name="Added", value=f"+{quantity:,}", inline=True)
            embed.add_field(
                name="New Total", value=f"{old_quantity + quantity:,}", inline=True
            )

            await interaction.response.send_message(embed=embed)
            await self.inventory.update_inventory_display(interaction.guild.id)
        else:
            await interaction.response.send_message(
                f"❌ Failed to add quantity for **{name}**.", ephemeral=True
            )

    @app_commands.describe(name="Name of the item to remove")
    async def remove_item(self, interaction: Interaction, name: str):
        """Remove an item from the inventory."""
        if not self.is_inventory_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to manage inventory.", ephemeral=True
            )
            return

        success = self.db.delete_item(interaction.guild.id, name)

        if success:
            embed = discord.Embed(
                title="✅ Item Removed",
                description=f"**{name}** has been removed from inventory.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed)
            await self.inventory.update_inventory_display(interaction.guild.id)
        else:
            await interaction.response.send_message(
                f"❌ Item **{name}** not found in inventory.", ephemeral=True
            )

    async def view_requests(self, interaction: Interaction):
        """View all pending requests."""
        if not self.is_inventory_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to manage inventory.", ephemeral=True
            )
            return

        requests = self.db.get_requests(interaction.guild.id, status="pending")

        if not requests:
            await interaction.response.send_message(
                "📭 No pending requests.", ephemeral=True
            )
            return

        embed = discord.Embed(title="📋 Pending Requests", color=discord.Color.orange())

        for request in requests[:10]:  # Show first 10 requests
            requested_items = json.loads(request.items)
            items_text = ", ".join(
                [f"{name} ({qty})" for name, qty in requested_items.items()]
            )

            embed.add_field(
                name=f"Request #{request.id} by {request.user_name}",
                value=f"{items_text}\n{format_for_discord(datetime.fromisoformat(request.created_at), guild_id=interaction.guild.id)}",
                inline=False,
            )

        if len(requests) > 10:
            embed.set_footer(
                text=f"Showing 10 of {len(requests)} requests. Use the buttons on request messages to approve/deny them."
            )
        else:
            embed.set_footer(
                text="Use the buttons on request messages to approve/deny them."
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.describe(request_id="ID of the request to approve")
    async def manual_approve_request(
        self, interaction: discord.Interaction, request_id: int
    ):
        """Manually approve a request (backup for when buttons don't work)."""
        if not self.is_inventory_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to manage inventory.", ephemeral=True
            )
            return

        request = self.db.get_request(request_id)
        if not request:
            await interaction.response.send_message(
                f"❌ Request #{request_id} not found.", ephemeral=True
            )
            return

        if request.guild_id != interaction.guild.id:
            await interaction.response.send_message(
                f"❌ Request #{request_id} doesn't belong to this server.",
                ephemeral=True,
            )
            return

        if request.status != "pending":
            await interaction.response.send_message(
                f"❌ Request #{request_id} is already {request.status}.", ephemeral=True
            )
            return

        # Update status first
        self.db.update_request_status(request_id, "approved")

        # Process the request (remove items from inventory)
        results = await self.inventory.process_approved_request(request)

        # Create response
        embed = discord.Embed(
            title="✅ Request Manually Approved",
            description=f"Request #{request_id} by {request.user_name} has been approved.",
            color=discord.Color.green(),
        )

        # Add processing results
        results_text = []
        for item_name, result in results.items():
            results_text.append(result)

        embed.add_field(
            name="Processing Results", value="\n".join(results_text), inline=False
        )
        embed.set_footer(
            text="💡 Tip: Use the buttons on request messages for easier approval!"
        )

        await interaction.response.send_message(embed=embed)

        # Try to notify the user
        try:
            user = self.bot.get_user(request.user_id)
            if user:
                user_embed = discord.Embed(
                    title="✅ Request Approved",
                    description=f"Your request #{request_id} has been approved!",
                    color=discord.Color.green(),
                )

                requested_items = json.loads(request.items)
                items_text = []
                for item_name, quantity in requested_items.items():
                    items_text.append(f"**{item_name}**: {quantity:,}")

                user_embed.add_field(
                    name="Approved Items", value="\n".join(items_text), inline=False
                )
                user_embed.set_footer(text=f"Server: {interaction.guild.name}")

                await user.send(embed=user_embed)
        except:
            pass  # User might have DMs disabled
