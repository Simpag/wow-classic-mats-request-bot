import json
import discord
from discord import Interaction, app_commands
from discord.ext import commands
from typing import Optional, List
from datetime import datetime

# Import from local modules
try:
    from .database import Database
    from .inventory_manager import InventoryManager
except ImportError:
    from database import Database
    from inventory_manager import InventoryManager


# Admin Commands Group
class AdminCommands(commands.Cog):
    def __init__(self, bot, database: Database):
        self.bot = bot
        self.db = database
        self.inventory = InventoryManager(bot, database)

        # Create admin group
        # Create admin commands group
        self.admin = app_commands.Group(
            name="admin", description="Admin commands for inventory management"
        )

        # Set default permissions to require Manage Guild (less restrictive than Administrator)
        # This will hide commands from regular users, but server admins can still grant access to specific roles
        self.admin.default_permissions = discord.Permissions(administrator=True)

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
    )
    async def setup(
        self,
        interaction: Interaction,
        channel: discord.TextChannel,
        admin_roles: Optional[str] = None,
    ):
        """Setup the inventory system."""
        # Only Discord administrators can perform initial setup
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
        )

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

        embed.add_field(
            name="Next Steps",
            value="• Use `/admin add_item` to add items to inventory\n• Users can use `/request` to request items\n• Use `/admin` commands to manage requests\n• Go to Server Settings > Integrations > Bot Name to grant `/admin` command access to the specified roles",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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

            await interaction.response.send_message(embed=embed, ephemeral=True)
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

            await interaction.response.send_message(embed=embed, ephemeral=True)
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

            await interaction.response.send_message(embed=embed, ephemeral=True)
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
                value=f"{items_text}\n{datetime.fromisoformat(request.created_at).strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False,
            )

        footer_txt = ""
        if len(requests) > 10:
            footer_txt = f"Showing 10 of {len(requests)} requests. Use the buttons on request messages to approve/deny them. "

        footer_txt += "Use the buttons on request messages to approve/deny them or use '/admin [manual_approve|manual_deny]'."

        embed.set_footer(text=footer_txt)

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

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Try to notify the user
        try:
            user = await self.bot.fetch_user(request.user_id)
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
