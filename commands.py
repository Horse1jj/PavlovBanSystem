import asyncio
import json
import requests
from base64 import b64decode
import discord
from discord import app_commands
from pavlov import PavlovRCON

# Load configuration
with open('config.json') as config_file:
    config = json.load(config_file)

required_roles = config["required_roles"]
bot_version = config.get("bot_version", "1.0.0")
programming_language = "Python 3.9"
log_channel_id = config["log_channel_id"]

def get_server_details(server_name, servers):
    return servers.get(server_name)

def has_required_role(user, required_roles):
    user_roles = [role.name for role in user.roles]
    for role in required_roles:
        if role in user_roles:
            return True
    return False

async def send_pavlov_command(host, port, password, command):
    try:
        pavlov = PavlovRCON(host, port, password)
        task = asyncio.create_task(pavlov.send(command))
        response = await task
        print(f"Pavlov response: {response}")
        return response if isinstance(response, str) else json.dumps(response)
    except Exception as e:
        print(f"Failed to send Pavlov command: {e}")
        return None

async def log_command(interaction, command_name, args):
    log_channel = interaction.guild.get_channel(log_channel_id)
    if log_channel:
        embed = discord.Embed(title="Command Used", color=discord.Color.blue())
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="Command", value=command_name, inline=True)
        embed.add_field(name="Arguments", value=str(args), inline=True)
        embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
        embed.add_field(name="Timestamp", value=interaction.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        await log_channel.send(embed=embed)

async def setup_commands(bot, servers, api_url, access_token):
    @bot.tree.command(name="kick", description="Kick a player from a server")
    @app_commands.describe(server_name="The name of the server", player_name="The name of the player to kick")
    async def kick(interaction: discord.Interaction, server_name: str, player_name: str):
        await log_command(interaction, "kick", {"server_name": server_name, "player_name": player_name})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        kick_command = f"kick {player_name}"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], kick_command)
        if response:
            await interaction.response.send_message(f"Player {player_name} kicked from {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to kick player {player_name} from {server_name}.", ephemeral=True)

    @bot.tree.command(name="rotatemap", description="Rotate map on a server")
    @app_commands.describe(server_name="The name of the server")
    async def rotatemap(interaction: discord.Interaction, server_name: str):
        await log_command(interaction, "rotatemap", {"server_name": server_name})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        rotate_command = "RotateMap"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], rotate_command)
        if response:
            await interaction.response.send_message(f"Map rotated on {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to rotate map on {server_name}.", ephemeral=True)

    @bot.tree.command(name="giveitem", description="Give an item to a player")
    @app_commands.describe(server_name="The name of the server", username="The name of the player", item_id="The ID of the item to give")
    async def giveitem(interaction: discord.Interaction, server_name: str, username: str, item_id: str):
        await log_command(interaction, "giveitem", {"server_name": server_name, "username": username, "item_id": item_id})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        give_item_command = f"giveitem {username} {item_id}"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], give_item_command)
        if response:
            await interaction.response.send_message(f"Item {item_id} given to {username} on {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to give item {item_id} to {username} on {server_name}.", ephemeral=True)

    @bot.tree.command(name="players", description="Get the list of players on a server")
    @app_commands.describe(server_name="The name of the server")
    async def players(interaction: discord.Interaction, server_name: str):
        await log_command(interaction, "players", {"server_name": server_name})

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        players_command = "RefreshList"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], players_command)
        print(f"Player list response: {response}")  # Debug print

        if response:
            try:
                player_list_data = json.loads(response)
                player_list = player_list_data.get('PlayerList', [])
                if player_list:
                    formatted_player_list = "\n".join([f"{player['Username']}" for player in player_list])
                    response_message = f"Current Players on {server_name}:\n```\n{formatted_player_list}\n```"
                    await interaction.response.send_message(response_message, ephemeral=True)
                else:
                    await interaction.response.send_message(f"No players currently on server '{server_name}'.", ephemeral=True)
            except json.JSONDecodeError:
                await interaction.response.send_message("Failed to parse player list response.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to retrieve player list for server '{server_name}'.", ephemeral=True)

    @bot.tree.command(name="banlist", description="Get the ban list for a server")
    @app_commands.describe(server_name="The name of the server")
    async def banlist(interaction: discord.Interaction, server_name: str):
        await log_command(interaction, "banlist", {"server_name": server_name})

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        banlist_command = "banlist"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], banlist_command)
        if response:
            try:
                ban_list_data = json.loads(response)
                banned_players = ban_list_data.get('BanList', [])
                if banned_players:
                    formatted_ban_list = "\n".join(banned_players)
                    response_message = f"Banned Players on {server_name}:\n```\n{formatted_ban_list}\n```"
                    await interaction.response.send_message(response_message, ephemeral=True)
                else:
                    await interaction.response.send_message(f"No banned players currently on server '{server_name}'.", ephemeral=True)
            except json.JSONDecodeError:
                await interaction.response.send_message("Failed to parse ban list response.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to retrieve ban list for server '{server_name}'.", ephemeral=True)

    @bot.tree.command(name="checkunban", description="Check unban time for a specific user")
    @app_commands.describe(username="The username to check")
    async def checkunban(interaction: discord.Interaction, username: str):
        await log_command(interaction, "checkunban", {"username": username})

        response = requests.get(api_url)
        if response.status_code == 200:
            data = json.loads(response.content.decode('utf-8'))

            if 'content' in data:
                raw_content = b64decode(data['content']).decode('utf-8')

                try:
                    banned_users = json.loads(raw_content)
                except json.JSONDecodeError as e:
                    await interaction.response.send_message(f"Error decoding JSON content: {e}", ephemeral=True)
                    return
            else:
                await interaction.response.send_message("No 'content' field found in data.", ephemeral=True)
                return
        else:
            await interaction.response.send_message(f"Failed to retrieve data from GitHub API. Status code: {response.status_code}", ephemeral=True)
            return

        if username in banned_users:
            ban_details = banned_users[username]
            banned_until = ban_details.get('banneduntil', 'N/A')
            ban_reason = ban_details.get('BanReason', 'N/A')
            await interaction.response.send_message(f"User {username} is banned until {banned_until} for reason: {ban_reason}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"User {username} is not found in the ban list.", ephemeral=True)

    @bot.tree.command(name="debug", description="DONT USE UNLESS NEEDED MAY BREAK BOT")
    async def debug(interaction: discord.Interaction):
        await log_command(interaction, "debug", {})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        debug_info = {
            "Version": bot_version,
            "Programming Language": programming_language,
            "Servers": ', '.join(servers.keys()),
            "API URL": api_url,
            "Commands": ', '.join([cmd.name for cmd in bot.tree.get_commands()]),
            "Bot Status": "Ready" if bot.is_ready() else "Not Ready"
        }

        embed = discord.Embed(title="Debug Information", color=discord.Color.blue())
        for key, value in debug_info.items():
            embed.add_field(name=key, value=value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="help", description="List all commands and their descriptions")
    async def help(interaction: discord.Interaction):
        await log_command(interaction, "help", {})

        embed = discord.Embed(title="Help - Command List", color=discord.Color.green())
        embed.add_field(name="/kick", value="Kick a player from a server. Required role: Admin, Moderator", inline=False)
        embed.add_field(name="/rotatemap", value="Rotate map on a server. Required role: Admin, Moderator", inline=False)
        embed.add_field(name="/giveitem", value="Give an item to a player. Required role: Admin, Moderator", inline=False)
        embed.add_field(name="/players", value="Get the list of players on a server. No required role", inline=False)
        embed.add_field(name="/banlist", value="Get the ban list for a server. No required role", inline=False)
        embed.add_field(name="/checkunban", value="Check unban time for a specific user. No required role", inline=False)
        embed.add_field(name="/debug", value="DONT USE UNLESS NEEDED MAY BREAK BOT. Required role: Admin, Moderator", inline=False)
        embed.add_field(name="/addmod", value="Add a player to the moderator list. Required role: Admin", inline=False)
        embed.add_field(name="/removemod", value="Remove a player from the moderator list. Required role: Admin", inline=False)
        embed.add_field(name="/ban", value="Ban a player from the server. Required role: Admin", inline=False)
        embed.add_field(name="/unban", value="Unban a player from the server. Required role: Admin", inline=False)
        embed.add_field(name="/setpin", value="Set or remove the server pin. Required role: Admin", inline=False)
        embed.add_field(name="/setmaxplayers", value="Set the maximum number of players on the server. Required role: Admin", inline=False)
        embed.add_field(name="/settimeLimit", value="Set the time limit for the current match. Required role: Admin", inline=False)
        embed.add_field(name="/setcash", value="Set the cash of a player. Required role: Admin", inline=False)
        embed.add_field(name="/givecash", value="Give cash to a player. Required role: Admin", inline=False)
        embed.add_field(name="/giveteamcash", value="Give cash to all players on a team. Required role: Admin", inline=False)
        embed.add_field(name="/slap", value="Deal damage to a player. Required role: Admin", inline=False)
        embed.add_field(name="/kill", value="Kill a player. Required role: Admin", inline=False)
        embed.add_field(name="/switchteam", value="Switch a player to another team. Required role: Admin", inline=False)
        embed.add_field(name="/teleport", value="Teleport a player to another player. Required role: Admin", inline=False)
        embed.add_field(name="/setplayerskin", value="Set the skin of a player. Required role: Admin", inline=False)
        embed.add_field(name="/setbalancetableurl", value="Set the balance table URL. Required role: Admin", inline=False)
        embed.add_field(name="/setlimitedammotype", value="Set the limited ammo type. Required role: Admin", inline=False)
        embed.add_field(name="/enablecompmode", value="Enable or disable competitive mode. Required role: Admin", inline=False)
        embed.add_field(name="/enableverboselogging", value="Enable or disable verbose logging. Required role: Admin", inline=False)
        embed.add_field(name="/enablewhitelist", value="Enable or disable whitelist usage. Required role: Admin", inline=False)
        embed.add_field(name="/showNametags", value="Enable or disable name tags above friendly players. Required role: Admin", inline=False)
        embed.add_field(name="/shutdownserver", value="Shutdown the server. Required role: Admin", inline=False)
        embed.add_field(name="/resetSND", value="Reset the currently running SND match. Required role: Admin", inline=False)
        embed.add_field(name="/pausematch", value="Pause the currently running match. Required role: Admin", inline=False)
        embed.add_field(name="/switchmap", value="Switch to a specific map and game mode. Required role: Admin", inline=False)
        embed.add_field(name="/addmaprotation", value="Add a map to the map rotation. Required role: Admin", inline=False)
        embed.add_field(name="/removemaprotation", value="Remove a map from the map rotation. Required role: Admin", inline=False)
        embed.add_field(name="/maplist", value="Get the current map rotation. Required role: Admin", inline=False)
        embed.add_field(name="/itemlist", value="List all items in the game. Required role: Admin", inline=False)
        embed.add_field(name="/inspectplayer", value="Get detailed status of a player. Required role: Admin", inline=False)
        embed.add_field(name="/inspectteam", value="Get detailed status of a team. Required role: Admin", inline=False)
        embed.add_field(name="/inspectall", value="Get detailed status of all players. Required role: Admin", inline=False)
        embed.add_field(name="/clearemptyvehicles", value="Clear all empty vehicles. Required role: Admin", inline=False)
        embed.add_field(name="/disconnect", value="Force the server to close the RCON connection. Required role: Admin", inline=False)
        embed.add_field(name="/updateservername", value="Update the server name. Required role: Admin", inline=False)
        embed.add_field(name="/ugcaddmod", value="Add a mod to the server. Required role: Admin", inline=False)
        embed.add_field(name="/ugcremovemod", value="Remove a mod from the server. Required role: Admin", inline=False)
        embed.add_field(name="/ugcclearmodlist", value="Clear all mods from the server. Required role: Admin", inline=False)
        embed.add_field(name="/ugcmodlist", value="List all mods on the server. Required role: Admin", inline=False)
        embed.add_field(name="/tttendround", value="End the TTT round. Required role: Admin", inline=False)
        embed.add_field(name="/tttflushkarma", value="Reset the karma of all players. Required role: Admin", inline=False)
        embed.add_field(name="/tttgivecredits", value="Give TTT credits to a player. Required role: Admin", inline=False)
        embed.add_field(name="/tttpausetimer", value="Pause the TTT timer. Required role: Admin", inline=False)
        embed.add_field(name="/tttsetkarma", value="Set the karma of a player. Required role: Admin", inline=False)
        embed.add_field(name="/tttsetrole", value="Set the TTT role of a player. Required role: Admin", inline=False)
        embed.add_field(name="/tttalwaysenableskinmenu", value="Enable or disable the TTT skin menu mid-round. Required role: Admin", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="addmod", description="Add a player to the moderator list")
    @app_commands.describe(server_name="The name of the server", unique_id="The unique ID of the player")
    async def addmod(interaction: discord.Interaction, server_name: str, unique_id: str):
        await log_command(interaction, "addmod", {"server_name": server_name, "unique_id": unique_id})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        addmod_command = f"AddMod {unique_id}"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], addmod_command)
        if response:
            await interaction.response.send_message(f"Player {unique_id} added to moderator list on {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to add player {unique_id} to moderator list on {server_name}.", ephemeral=True)


    @bot.tree.command(name="setpin", description="Set or remove the server pin")
    @app_commands.describe(server_name="The name of the server", pin="The pin number (optional)")
    async def setpin(interaction: discord.Interaction, server_name: str, pin: str = None):
        await log_command(interaction, "setpin", {"server_name": server_name, "pin": pin})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        setpin_command = f"SetPin {pin}" if pin else "SetPin"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], setpin_command)
        if response:
            await interaction.response.send_message(f"Server pin {'set' if pin else 'removed'} on {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to {'set' if pin else 'remove'} server pin on {server_name}.", ephemeral=True)

    # Additional commands
    @bot.tree.command(name="ban", description="Ban a player from the server")
    @app_commands.describe(server_name="The name of the server", player_name="The name of the player to ban")
    async def Ban(interaction: discord.Interaction, server_name: str, player_name: str):
        await log_command(interaction, "ban", {"server_name": server_name, "player_name": player_name})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        ban_command = f"Ban {player_name}"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], ban_command)
        if response:
            await interaction.response.send_message(f"Player {player_name} banned from {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to ban player {player_name} from {server_name}.", ephemeral=True)

    @bot.tree.command(name="unban", description="Unban a player from the server")
    @app_commands.describe(server_name="The name of the server", player_name="The name of the player to unban")
    async def Unban(interaction: discord.Interaction, server_name: str, player_name: str):
        await log_command(interaction, "unban", {"server_name": server_name, "player_name": player_name})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        unban_command = f"Unban {player_name}"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], unban_command)
        if response:
            await interaction.response.send_message(f"Player {player_name} unbanned on {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to unban player {player_name} on {server_name}.", ephemeral=True)

    @bot.tree.command(name="GiveRCONplus", description="Gives RCON plus menu")
    @app_commands.describe(server_name="The name of the server", username="the username")
    async def GiveRCONplus(interaction: discord.Interaction, server_name: str, username: str):
        await log_command(interaction, "GiveRCONplus", {"server_name": server_name, "username": username})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        setpin_command = f"GiveMenu {username}"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], setpin_command)
        if response:
            await interaction.response.send_message(f"RCON plus  Given to {usermame} on {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to give RCON on {server_name}.", ephemeral=True)

    @bot.tree.command(name="setmaxplayers", description="Set the maximum number of players on the server")
    @app_commands.describe(server_name="The name of the server", max_players="The maximum number of players")
    async def SetMaxPlayers(interaction: discord.Interaction, server_name: str, max_players: int):
        await log_command(interaction, "setmaxplayers", {"server_name": server_name, "max_players": max_players})

        if not has_required_role(interaction.user, required_roles):
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        setmaxplayers_command = f"SetMaxPlayers {max_players}"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], setmaxplayers_command)
        if response:
            await interaction.response.send_message(f"Maximum players set to {max_players} on {server_name}.\nResponse: {response}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to set max players on {server_name}.", ephemeral=True)

    @bot.tree.command(name="addmod", description="Add a moderator to the server")
    @app_commands.describe(server_name="The name of the server", player_name="The name of the player to add as moderator")
    async def AddMod(interaction: discord.Interaction, server_name: str, player_name: str):
        await log_command(interaction, "addmod", {"server_name": server_name, "player_name": player_name})

        server_details = get_server_details(server_name, servers)
        if not server_details:
            await interaction.response.send_message(f"Server '{server_name}' not found.", ephemeral=True)
            return

        addmod_command = f"AddMod {player_name}"
        response = await send_pavlov_command(server_details['ip'], server_details['port'], server_details['password'], addmod_command)
        await interaction.response.send_message(f"Response: {response}", ephemeral=True)

    

