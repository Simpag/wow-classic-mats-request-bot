# WoW Classic Materials Request Bot - Quick Start

## ✅ Setup Complete!

Your Discord bot is now ready for WoW Classic guild inventory management. Here's what you have:

### 📁 **Project Structure**
```
wow-classic-mats-request-bot/
├── main.py              # Original bot file (updated with inventory system)
├── run.py               # Standalone bot runner (recommended)
├── test_setup.py        # Test script to validate setup
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── README.md           # Comprehensive documentation
└── src/                # Bot modules
    ├── database.py     # SQLite database management
    ├── inventory_manager.py  # Inventory display and logic
    └── commands.py     # Discord slash commands
```

### 🚀 **Quick Start Steps**

1. **Set up your Discord bot token:**
   ```bash
   cp .env.example .env
   # Edit .env and add your Discord bot token
   ```

2. **Update your Guild ID:**
   Edit `run.py` and replace `1402810501058134151` with your Discord server's ID

3. **Run the bot:**
   ```bash
   python run.py
   ```

### 🎮 **Available Commands**

#### **Setup (Admin Only)**
- `/setup` - Configure inventory channel and admin roles

#### **User Commands**
- `/inventory` - View current guild inventory
- `/request` - Request items (e.g., "Iron Ore: 50, Copper Ore: 100")
  - Creates a **public announcement** with approve/deny buttons for admins
  - Posts in the configured inventory channel or current channel
  - Sends confirmation DM to the requester
- `/my_requests` - View your request history

#### **Admin Commands**
- `/admin add_item` - Add items to inventory
- `/admin set_quantity` - Set exact item quantities
- `/admin add_quantity` - Add to existing quantities
- `/admin remove_item` - Remove items completely
- `/admin requests` - View pending requests
- **✅ Interactive Buttons** - Use approve/deny buttons on request messages (recommended)
- `/admin manual_approve` - Backup command to approve requests by ID

### 📊 **Features**
- ✅ **Auto-updating inventory display** in designated channel
- ✅ **SQLite database** for reliable storage across multiple servers
- ✅ **Role-based permissions** for inventory management
- ✅ **Flexible item request formats**
- ✅ **PUBLIC REQUEST ANNOUNCEMENTS** with interactive approve/deny buttons
- ✅ **Automatic inventory deduction** on approval
- ✅ **User notifications** via DM when requests are processed
- ✅ **Real-time stock availability** shown on requests
- ✅ **Visual status indicators** (Available/Low Stock/Out of Stock)

### 🔧 **Bot Permissions Required**
Make sure your Discord bot has these permissions:
- Send Messages
- Use Slash Commands
- Embed Links
- Read Message History
- Manage Messages (for updating inventory display)

### 🐛 **Testing**
Run `python test_setup.py` to validate everything is working correctly.

---

**Need help?** Check the full `README.md` for detailed documentation and examples!
