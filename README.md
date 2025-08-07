# WoW Classic Materials Request Bot

A Discord bot designed for World of Warcraft Classic guilds to manage materials and item requests. The bot allows admins to maintain an inventory of materials and guild members to request items, with automatic inventory tracking and notifications.

## Features

### 🏛️ **Inventory Management**
- **Auto-updating inventory display** in a designated channel
- **Add/remove items** with quantities and descriptions
- **Visual status indicators** (Available, Low Stock, Out of Stock)
- **Real-time updates** when items are added or removed

### 📋 **Request System**
- **User-friendly item requests** with flexible input formats
- **Admin approval/denial** workflow
- **Automatic inventory deduction** on approval
- **User notifications** via DM
- **Request history tracking**

### ⚙️ **Administration**
- **Role-based permissions** for inventory management
- **Simple setup** with `/setup` command
- **Comprehensive admin tools** for managing items and requests
- **SQLite database** for reliable data storage

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd wow-classic-mats-request-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create environment file**
   Create a `.env` file in the root directory:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

4. **Update Guild ID**
   In `run.py`, replace the `GUILD_ID` with your Discord server's ID:
   ```python
   GUILD_ID = Object(id=YOUR_GUILD_ID_HERE)
   ```

5. **Run the bot**
   ```bash
   python run.py
   ```

## Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Copy the bot token to your `.env` file
4. Invite the bot to your server with the following permissions:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History
   - Manage Messages (for updating inventory display)

## Commands

### 🔧 **Setup Commands**

#### `/setup`
**Description:** Configure the inventory system for your server
**Parameters:**
- `channel` (required): Channel where inventory will be displayed
- `admin_roles` (optional): Comma-separated list of roles that can manage inventory

**Example:**
```
/setup channel:#materials admin_roles:Officer,Guild Master
```

### 👤 **User Commands**

#### `/inventory`
**Description:** View the current guild inventory

#### `/request`
**Description:** Request items from the guild inventory
**Parameters:**
- `items`: Items to request in flexible formats

**Supported formats:**
- `Iron Ore: 50, Copper Ore: 100`
- `Iron Ore 50, Copper Ore 100`
- `Iron Ore x50, Copper Ore x100`

**Example:**
```
/request items:Iron Ore: 50, Copper Ore: 100, Heavy Leather x25
```

#### `/my_requests`
**Description:** View your pending and processed requests

### 🛡️ **Admin Commands**

#### `/admin add_item`
**Description:** Add a new item to the inventory
**Parameters:**
- `name` (required): Name of the item
- `quantity` (optional): Initial quantity (default: 0)
- `description` (optional): Item description

**Example:**
```
/admin add_item name:Iron Ore quantity:500 description:Used for blacksmithing
```

#### `/admin set_quantity`
**Description:** Set the exact quantity of an item
**Parameters:**
- `name` (required): Item name
- `quantity` (required): New quantity

#### `/admin add_quantity`
**Description:** Add to the current quantity of an item
**Parameters:**
- `name` (required): Item name
- `quantity` (required): Amount to add

#### `/admin remove_item`
**Description:** Completely remove an item from inventory
**Parameters:**
- `name` (required): Item name to remove

#### `/admin requests`
**Description:** View all pending requests

#### `/admin approve_request`
**Description:** Approve a pending request (automatically removes items)
**Parameters:**
- `request_id` (required): ID of the request to approve

#### `/admin deny_request`
**Description:** Deny a pending request
**Parameters:**
- `request_id` (required): ID of the request to deny
- `reason` (optional): Reason for denial

## Database Structure

The bot uses SQLite with three main tables:

### guild_configs
- Stores per-server configuration
- Inventory channel and message IDs
- Admin role permissions

### items
- Guild inventory items
- Name, quantity, description
- Unique per guild

### item_requests
- User requests for items
- Status tracking (pending/approved/denied)
- Timestamps and user information

## Permissions System

**Server Administrators:** Full access to all commands

**Custom Admin Roles:** Set via `/setup` command
- Can manage inventory (add/remove items)
- Can approve/deny requests
- Cannot change server configuration

**Regular Users:** 
- Can view inventory
- Can create requests
- Can view their own requests

## Usage Examples

### Initial Setup
1. Admin runs `/setup channel:#guild-bank admin_roles:Officer`
2. Bot creates an auto-updating inventory display in #guild-bank
3. Officers can now manage inventory

### Adding Materials
1. Officer runs `/admin add_item name:Iron Ore quantity:1000 description:For guild crafting`
2. Inventory display automatically updates
3. Item is now available for requests

### User Request Flow
1. Member runs `/request items:Iron Ore: 50, Heavy Leather x25`
2. Bot validates items exist in inventory
3. Creates pending request with unique ID
4. Officer reviews with `/admin requests`
5. Officer approves with `/admin approve_request request_id:1`
6. Items automatically removed from inventory
7. User receives DM notification
8. Inventory display updates

### Inventory Management
```bash
# Add new items
/admin add_item name:Copper Ore quantity:500

# Restock existing items
/admin add_quantity name:Iron Ore quantity:200

# Set exact amounts
/admin set_quantity name:Heavy Leather quantity:50

# Remove items entirely
/admin remove_item name:Light Leather
```

## Troubleshooting

### Bot not responding to commands
- Ensure bot has proper permissions in your server
- Check that commands are synced (look for sync message on startup)
- Verify your guild ID is correct in `run.py`

### Import errors when running
- Make sure you're running from the project root directory
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Try running with `python run.py` instead of `python main.py`

### Commands not syncing
- Set `SHOULD_SYNC = True` in `run.py`
- Restart the bot
- Commands are guild-specific, make sure you're testing in the right server

### Database issues
- The SQLite database (`inventory.db`) is created automatically
- If you need to reset: stop bot, delete `inventory.db`, restart bot
- Database is created in the same directory as the bot

## Customization

### Changing Guild ID
Edit `run.py` and update the `GUILD_ID` variable:
```python
GUILD_ID = Object(id=YOUR_GUILD_ID_HERE)
```

### Adding More Item Categories
You can extend the database schema in `src/database.py` to add categories, item types, or other metadata.

### Customizing Embed Colors
Edit the color schemes in `src/inventory_manager.py`:
```python
color_map = {
    'pending': Color.orange(),
    'approved': Color.green(),
    'denied': Color.red()
}
```

## Contributing

Feel free to submit issues, feature requests, or pull requests. This bot is designed to be easily extensible for different guild needs.

## License

[Add your license information here]
