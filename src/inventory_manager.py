import json
import discord
from discord import Embed, Color, ui, ButtonStyle
from discord.ext import commands
from typing import Dict, List, Optional
from datetime import datetime, timezone

try:
    from .database import Database, Item, ItemRequest
except ImportError:
    from database import Database, Item, ItemRequest


class InventoryManager:
    def __init__(self, bot, database: Database):
        self.bot = bot
        self.db = database

    def create_inventory_embed(self, guild_id: int) -> Embed:
        """Create an embed showing the current inventory."""
        items = self.db.get_items(guild_id)

        embed = Embed(
            title="🏛️ Guild Inventory",
            description="Current materials and items available",
            color=Color.blue(),
            timestamp=datetime.now(),
        )

        if not items:
            embed.add_field(
                name="📦 No Items",
                value="The inventory is currently empty.\nAdmins can add items using `/admin add_item`",
                inline=False,
            )
            return embed

        # Group items by quantity status
        available_items = []
        low_stock_items = []
        out_of_stock_items = []

        for item in items:
            item_line = f"**{item.name}**: {item.quantity:,}"
            if item.description:
                item_line += f" _{item.description}_"

            if item.quantity == 0:
                out_of_stock_items.append(item_line)
            elif item.quantity < 10:  # Consider < 10 as low stock
                low_stock_items.append(item_line)
            else:
                available_items.append(item_line)

        # Add available items
        if available_items:
            embed.add_field(
                name="✅ Available Items",
                value="\n".join(
                    available_items[:10]
                ),  # Limit to prevent embed size issues
                inline=True,
            )
            if len(available_items) > 10:
                embed.add_field(
                    name="➕ More Available",
                    value=f"... and {len(available_items) - 10} more items",
                    inline=True,
                )

        # Add low stock items
        if low_stock_items:
            embed.add_field(
                name="⚠️ Low Stock", value="\n".join(low_stock_items[:10]), inline=True
            )

        # Add out of stock items
        if out_of_stock_items:
            embed.add_field(
                name="❌ Out of Stock",
                value="\n".join(out_of_stock_items[:10]),
                inline=True,
            )

        # Add footer with instructions
        embed.set_footer(
            text="Use /request to request items • Use /admin commands to manage inventory"
        )

        return embed

    async def update_inventory_display(self, guild_id: int) -> bool:
        """Update the inventory display message in the designated channel."""
        config = self.db.get_guild_config(guild_id)
        if not config or not config.inventory_channel_id:
            return False

        try:
            channel = self.bot.get_channel(config.inventory_channel_id)
            if not channel:
                return False

            embed = self.create_inventory_embed(guild_id)

            # If we have a message ID, try to edit it
            if config.inventory_message_id:
                try:
                    message = await channel.fetch_message(config.inventory_message_id)
                    await message.edit(embed=embed)
                except discord.NotFound:
                    # Message was deleted, create a new one
                    pass
            else:
                # Create new message
                message = await channel.send(embed=embed)
                self.db.set_guild_config(guild_id, inventory_message_id=message.id)

            # Update pending request messages with new availability
            await self.update_pending_request_messages(guild_id)

            return True

        except Exception as e:
            print(f"Error updating inventory display for guild {guild_id}: {e}")
            return False

    def parse_item_input(self, input_text: str) -> Dict[str, int]:
        """Parse item input from user. Supports formats like:
        - 'Iron Ore: 50, Copper Ore: 100'
        - 'Iron Ore 50, Copper Ore 100'
        - 'Iron Ore x50, Copper Ore x100'
        """
        items = {}

        # Split by commas first
        parts = [part.strip() for part in input_text.split(",")]

        for part in parts:
            # Try different formats
            if ":" in part:
                # Format: "Item Name: 50"
                name, quantity = part.split(":", 1)
                name = name.strip()
                quantity = quantity.strip()
            elif " x" in part.lower():
                # Format: "Item Name x50"
                name, quantity = part.lower().split(" x", 1)
                name = name.strip()
                quantity = quantity.strip()
            else:
                # Format: "Item Name 50" - take last word as quantity
                words = part.split()
                if len(words) < 2:
                    continue
                quantity = words[-1]
                name = " ".join(words[:-1])

            # Try to convert quantity to int
            try:
                quantity = int(quantity.replace(",", ""))
                if quantity > 0:
                    items[name] = quantity
            except ValueError:
                continue

        return items

    def is_admin(self, member: discord.Member, guild_id: int) -> bool:
        """Check if a member is an admin for inventory management."""
        # Server administrators always have access
        if member.guild_permissions.administrator:
            return True

        # Check for specific admin roles
        config = self.db.get_guild_config(guild_id)
        if config and config.admin_role_ids:
            try:
                admin_role_ids = json.loads(config.admin_role_ids)
                member_role_ids = [role.id for role in member.roles]
                if any(role_id in admin_role_ids for role_id in member_role_ids):
                    return True
            except (json.JSONDecodeError, AttributeError):
                pass

        return False

    async def process_approved_request(self, request: ItemRequest) -> Dict[str, str]:
        """Process an approved request by removing items from inventory.
        Returns a dict with results for each item."""
        requested_items = json.loads(request.items)
        results = {}

        for item_name, requested_qty in requested_items.items():
            will_remove = requested_qty
            current_item = self.db.get_item(request.guild_id, item_name)

            if not current_item:
                results[item_name] = f"❌ **{item_name}**: Not found in inventory"
                continue

            if current_item.quantity < requested_qty:
                will_remove = current_item.quantity

            # Remove the items
            success = self.db.remove_item_quantity(
                request.guild_id, item_name, will_remove
            )
            if success:
                results[item_name] = (
                    f"✅ **{item_name}**: Rewarded {will_remove}/{requested_qty} (remaining: {current_item.quantity - will_remove})"
                    if will_remove == requested_qty
                    else f"⚠️ **{item_name}**: Rewarded {will_remove}/{requested_qty} (remaining: {current_item.quantity - will_remove})"
                )
            else:
                results[item_name] = f"❌ **{item_name}**: Failed to remove items"

        # Update the inventory display
        await self.update_inventory_display(request.guild_id)

        return results

    def create_public_request_embed(
        self, request: ItemRequest, user: discord.Member = None
    ) -> Embed:
        """Create a public embed for a new request that everyone can see."""
        requested_items = json.loads(request.items)

        embed = Embed(
            title=f"📋 New Item Request #{request.id}",
            description=f"Request by {request.user_name}",
            color=Color.orange(),
            # timestamp=datetime.fromisoformat(request.created_at),
        )

        # Add user avatar if available
        if user and user.avatar:
            embed.set_thumbnail(url=user.avatar.url)

        # Add requested items with availability check
        items_text = []
        availability_text = []

        for item_name, quantity in requested_items.items():
            items_text.append(f"**{item_name}**: {quantity:,}")

            # Check current stock
            current_item = self.db.get_item(request.guild_id, item_name)
            if current_item:
                if current_item.quantity >= quantity:
                    availability_text.append(
                        f"✅ **{item_name}**: {current_item.quantity:,} available"
                    )
                else:
                    availability_text.append(
                        f"⚠️ **{item_name}**: Only {current_item.quantity:,} available (need {quantity:,})"
                    )
            else:
                availability_text.append(f"❌ **{item_name}**: Not found in inventory")

        embed.add_field(
            name="Requested Items", value="\n".join(items_text), inline=False
        )

        embed.add_field(
            name="Current Availability",
            value="\n".join(availability_text),
            inline=False,
        )

        embed.add_field(name="Status", value="🟡 Pending Review", inline=True)

        # Parse the datetime and assume it's UTC if no timezone info
        request_time = datetime.fromisoformat(request.created_at)
        if request_time.tzinfo is None:
            request_time = request_time.replace(tzinfo=timezone.utc)

        embed.add_field(
            name="Requested",
            value=f"<t:{int(request_time.timestamp())}:R>",
            inline=True,
        )

        embed.set_footer(text=f"Request ID: {request.id} • User ID: {request.user_id}")

        return embed

    async def update_pending_request_messages(self, guild_id: int) -> None:
        """Update the availability information in all pending request messages."""
        try:
            # Get all pending requests for this guild
            pending_requests = []
            # We need to add a method to get pending requests, let's use the database
            # For now, let's get the guild config to find the inventory channel
            guild_config = self.db.get_guild_config(guild_id)
            if not guild_config or not guild_config.inventory_channel_id:
                return

            channel = self.bot.get_channel(guild_config.inventory_channel_id)
            if not channel:
                return

            # Search through recent messages in the inventory channel for pending requests
            # We'll look at the last 100 messages (Discord API limit for history without pagination)
            async for message in channel.history(limit=100):
                if (
                    message.author == self.bot.user
                    and message.embeds
                    and message.embeds[0].title
                    and "New Item Request #" in message.embeds[0].title
                    and "🟡 Pending Review" in str(message.embeds[0].fields)
                ):

                    # Extract request ID from title
                    import re

                    match = re.search(r"#(\d+)", message.embeds[0].title)
                    if match:
                        request_id = int(match.group(1))

                        # Get the request from database to make sure it's still pending
                        request = self.db.get_request(request_id)
                        if request and request.status == "pending":
                            # Update the message with current availability
                            try:
                                user = await self.bot.fetch_user(request.user_id)
                                updated_embed = self.create_public_request_embed(
                                    request=request, user=user
                                )
                                await message.edit(embed=updated_embed)
                            except Exception as e:
                                print(
                                    f"Failed to update request message {message.id}: {e}"
                                )
                                continue

            print(f"✅ Updated pending request messages for guild {guild_id}")

        except Exception as e:
            print(f"Error updating pending request messages for guild {guild_id}: {e}")


class PersistentRequestView(ui.View):
    """Persistent view that survives bot restarts."""

    def __init__(
        self,
        bot: commands.Bot = None,
        database: Database = None,
        inventory_manager: InventoryManager = None,
    ):
        super().__init__(timeout=None)  # Persistent views must have timeout=None
        self.bot = bot
        self.db = database
        self.inventory = inventory_manager

    def set_dependencies(
        self, bot: commands.Bot, database: Database, inventory_manager: InventoryManager
    ):
        """Set the dependencies after bot restart."""
        self.bot = bot
        self.db = database
        self.inventory = inventory_manager

    @ui.button(
        label="✅ Approve", style=ButtonStyle.green, custom_id="persistent_approve"
    )
    async def approve_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle approve button click."""
        # Extract request ID from the embed
        embed = interaction.message.embeds[0]
        title = embed.title
        request_id = None

        # Parse request ID from title like "📋 New Item Request #123" or "📋 Request #123 - ✅ APPROVED"
        import re

        match = re.search(r"#(\d+)", title)
        if match:
            request_id = int(match.group(1))

        if not request_id:
            await interaction.response.send_message(
                "❌ Could not find request ID.", ephemeral=True
            )
            return

        # Check permissions
        if not self.inventory.is_admin(interaction.user, interaction.guild.id):
            await interaction.response.send_message(
                "❌ You don't have permission to approve requests.", ephemeral=True
            )
            return

        await interaction.response.defer()

        request = self.db.get_request(request_id)
        if not request:
            await interaction.followup.send("❌ Request not found.", ephemeral=True)
            return

        if request.status != "pending":
            await interaction.followup.send(
                f"❌ Request is already {request.status}.", ephemeral=True
            )
            return

        # Update status first
        self.db.update_request_status(request_id, "approved")

        # Process the request (remove items from inventory)
        results = await self.inventory.process_approved_request(request)

        # Update the embed to show approved status
        embed.color = Color.green()
        embed.title = f"📋 Request #{request_id} - ✅ APPROVED"

        # Add processing results
        results_text = []
        for item_name, result in results.items():
            results_text.append(result)

        # Update or add the results field
        embed.clear_fields()

        # Re-add original request info
        requested_items = json.loads(request.items)
        items_text = []
        for item_name, quantity in requested_items.items():
            items_text.append(f"**{item_name}**: {quantity:,}")

        embed.add_field(
            name="Requested Items", value="\n".join(items_text), inline=False
        )
        embed.add_field(
            name="Processing Results", value="\n".join(results_text), inline=False
        )
        embed.add_field(name="Approved by", value=interaction.user.mention, inline=True)
        embed.add_field(
            name="Approved at",
            value=f"<t:{int(datetime.now().timestamp())}:R>",
            inline=True,
        )

        # Disable buttons
        for item in self.children:
            item.disabled = True

        await interaction.edit_original_response(embed=embed, view=self)

        # Try to notify the user via DM
        try:
            user = await self.bot.fetch_user(request.user_id)
            if user:
                user_embed = discord.Embed(
                    title="✅ Request Approved!",
                    description=f"Your request has been approved and processed!",
                    color=discord.Color.green(),
                )
                user_embed.add_field(
                    name="Approved Items", value="\n".join(results_text), inline=False
                )
                user_embed.add_field(
                    name="Server", value=interaction.guild.name, inline=True
                )
                user_embed.add_field(name="Request ID", value=request_id, inline=True)
                user_embed.add_field(
                    name="Approved by", value=interaction.user.display_name, inline=True
                )
                await user.send(embed=user_embed)
        except Exception as e:
            print(f"Could not send DM to user {request.user_id}: {e}")

    @ui.button(label="❌ Deny", style=ButtonStyle.red, custom_id="persistent_deny")
    async def deny_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle deny button click."""
        # Extract request ID from the embed
        embed = interaction.message.embeds[0]
        title = embed.title
        request_id = None

        # Parse request ID from title
        import re

        match = re.search(r"#(\d+)", title)
        if match:
            request_id = int(match.group(1))

        if not request_id:
            await interaction.response.send_message(
                "❌ Could not find request ID.", ephemeral=True
            )
            return

        # Check permissions
        if not self.inventory.is_admin(interaction.user, interaction.guild.id):
            await interaction.response.send_message(
                "❌ You don't have permission to deny requests.", ephemeral=True
            )
            return

        # Create a modal for denial reason
        modal = PersistentDenyReasonModal(
            self.bot, self.db, self.inventory, request_id, self
        )
        await interaction.response.send_modal(modal)


class PersistentDenyReasonModal(ui.Modal, title="Deny Request"):
    """Modal for entering denial reason."""

    def __init__(
        self,
        bot: commands.Bot,
        database: Database,
        inventory_manager: InventoryManager,
        request_id: int,
        view: PersistentRequestView,
    ):
        super().__init__()
        self.bot = bot
        self.db = database
        self.inventory = inventory_manager
        self.request_id = request_id
        self.view = view

    reason = ui.TextInput(
        label="Reason for denial (optional)",
        placeholder="Enter reason why this request is being denied...",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph,
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        await interaction.response.defer()

        request = self.db.get_request(self.request_id)
        if not request:
            await interaction.followup.send("❌ Request not found.", ephemeral=True)
            return

        if request.status != "pending":
            await interaction.followup.send(
                f"❌ Request is already {request.status}.", ephemeral=True
            )
            return

        # Update status
        self.db.update_request_status(self.request_id, "denied")

        # Update the embed to show denied status
        embed = interaction.message.embeds[0]
        embed.color = Color.red()
        embed.title = f"📋 Request #{self.request_id} - ❌ DENIED"

        # Clear fields and re-add
        embed.clear_fields()

        # Re-add original request info
        requested_items = json.loads(request.items)
        items_text = []
        for item_name, quantity in requested_items.items():
            items_text.append(f"**{item_name}**: {quantity:,}")

        embed.add_field(
            name="Requested Items", value="\n".join(items_text), inline=False
        )
        if self.reason.value:
            embed.add_field(name="Denial Reason", value=self.reason.value, inline=False)
        embed.add_field(name="Denied by", value=interaction.user.mention, inline=True)
        embed.add_field(
            name="Denied at",
            value=f"<t:{int(datetime.now().timestamp())}:R>",
            inline=True,
        )

        # Disable all buttons
        for item in self.view.children:
            item.disabled = True

        await interaction.edit_original_response(embed=embed, view=self.view)

        # Try to notify the user via DM
        try:
            user = await self.bot.fetch_user(request.user_id)
            if user:
                user_embed = discord.Embed(
                    title="❌ Request Denied",
                    description=f"Your request has been denied.",
                    color=discord.Color.red(),
                )
                user_embed.add_field(
                    name="Requested Items", value="\n".join(items_text), inline=False
                )
                if self.reason.value:
                    user_embed.add_field(
                        name="Reason", value=self.reason.value, inline=False
                    )
                user_embed.add_field(
                    name="Server", value=interaction.guild.name, inline=True
                )
                user_embed.add_field(
                    name="Request ID", value=self.request_id, inline=True
                )
                user_embed.add_field(
                    name="Denied by", value=interaction.user.display_name, inline=True
                )
                await user.send(embed=user_embed)
        except Exception as e:
            print(f"Could not send DM to user {request.user_id}: {e}")
