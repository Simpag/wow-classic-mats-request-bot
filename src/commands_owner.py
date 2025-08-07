import discord
from discord.ext import commands


class OwnerCommands(commands.Cog):
    def __init__(self, bot, guild_id: int, owner_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.owner_id = owner_id

    # Define sync commands outside the class
    @commands.command(name="sync")
    async def sync_commands(self, ctx, scope: str = "guild"):
        """
        Manually sync slash commands. Owner only.
        Usage: !sync [guild|global]
        """
        if ctx.author.id != self.owner_id:
            await ctx.send("❌ Only the bot owner can use this command.")
            return

        try:
            bot = ctx.bot
            # Show current commands in tree
            commands_in_tree = list(bot.tree.get_commands())
            await ctx.send(f"📋 Commands in tree: {len(commands_in_tree)}")
            for cmd in commands_in_tree:
                await ctx.send(f"  - {cmd.name} (type: {type(cmd).__name__})")

            # Sync based on scope
            if scope.lower() == "global":
                await ctx.send("🔄 Syncing commands globally...")
                synced = await bot.tree.sync()
                scope_text = "globally"
            else:
                await ctx.send(f"🔄 Syncing commands to guild {self.guild_id}...")
                guild_obj = discord.Object(id=self.guild_id)
                synced = await bot.tree.sync(guild=guild_obj)
                scope_text = "to the guild"

            embed = discord.Embed(
                title="✅ Commands Synced",
                description=f"Successfully synced {len(synced)} commands {scope_text}.",
                color=discord.Color.green(),
            )

            if synced:
                command_list = "\n".join([f"• {cmd.name}" for cmd in synced])
                embed.add_field(
                    name="Synced Commands", value=command_list, inline=False
                )
            else:
                embed.add_field(
                    name="Note",
                    value="No commands were synced. This might indicate an issue.",
                    inline=False,
                )

            embed.add_field(name="Scope", value=scope_text.title(), inline=True)
            embed.set_footer(
                text="Use '!sync global' for global sync or '!sync guild' for guild-specific sync"
            )

            await ctx.send(embed=embed)
            print(
                f"Manual sync ({scope}): {len(synced)} commands synced by {ctx.author}"
            )

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Sync Failed",
                description=f"Failed to sync commands: {str(e)}",
                color=discord.Color.red(),
            )
            await ctx.send(embed=error_embed)
            print(f"Manual sync failed: {e}")

    @commands.command(name="clear")
    async def clear_commands(self, ctx, scope: str = "guild"):
        """
        Clear all synced slash commands. Owner only.
        Usage: !clear [guild|global]
        """
        if ctx.author.id != self.owner_id:
            await ctx.send("❌ Only the bot owner can use this command.")
            return

        try:
            bot = ctx.bot
            # Clear commands based on scope
            if scope.lower() == "global":
                await ctx.send("🧹 Clearing all global commands...")
                bot.tree.clear_commands(guild=None)
                await bot.tree.sync()
                scope_text = "globally"
            else:
                await ctx.send(f"🧹 Clearing commands from guild {self.guild_id}...")
                guild_obj = discord.Object(id=self.guild_id)
                bot.tree.clear_commands(guild=guild_obj)
                await bot.tree.sync(guild=guild_obj)
                scope_text = "from the guild"

            embed = discord.Embed(
                title="✅ Commands Cleared",
                description=f"Successfully cleared all commands {scope_text}.",
                color=discord.Color.orange(),
            )
            embed.add_field(name="Scope", value=scope_text.title(), inline=True)
            embed.set_footer(text="Use '!sync' to re-sync commands after clearing")

            await ctx.send(embed=embed)
            print(f"Manual clear ({scope}): Commands cleared by {ctx.author}")

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Clear Failed",
                description=f"Failed to clear commands: {str(e)}",
                color=discord.Color.red(),
            )
            await ctx.send(embed=error_embed)
            print(f"Manual clear failed: {e}")
