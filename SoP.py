import discord
import discord.app_commands
import sqlite3
import os
import sys
import json

# Funzione per leggere i punti di un utente
def get_points(user_id):
    with open("SoP.jsonl", "r") as file:
        for line in file:
            data = json.loads(line)
            if data["user_id"] == user_id:
                return data["points"]
    return 0  # Se l'utente non esiste, restituisce 0 punti

# Funzione per aggiornare i punti di un utente
def add_points(user_id, amount):
    users = []

    with open("SoP.jsonl", "r") as file:
        users = [json.loads(line) for line in file]

    updated = False
    for user in users:
        if user["user_id"] == user_id:
            user["points"] += amount
            updated = True
            break
    
    if not updated:
        users.append({"user_id": user_id, "points": amount})

    with open("SoP.jsonl", "w") as file:
        for user in users:
            file.write(json.dumps(user) + "\n")


# Imposta gli intent
intents = discord.Intents.default()
intents.message_content = True

# Classe del bot
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def on_ready(self):
        try:
            await self.tree.sync()
            print(f'{self.user} è online!')
        except Exception as e:
            print(f"Errore critico: {e}")
            restart_bot()  # 🔄 Riavvia il bot in caso di errore grave

# Funzione di riavvio automatico
def restart_bot():
    """Riavvia il bot automaticamente in caso di crash."""
    os.execv(sys.executable, ['python'] + sys.argv)

# Inizializza il bot
bot = MyBot()

# Funzioni per gestire il database SQLite
def add_points(user_id, amount):
    """Aggiunge punti a un utente e li salva su SQLite."""
    conn = sqlite3.connect("points_database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT points FROM points WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result:  # Se l'utente esiste, aggiorna i punti
        new_points = result[0] + amount
        cursor.execute("UPDATE points SET points = ? WHERE user_id = ?", (new_points, user_id))
    else:  # Se l'utente non esiste, lo aggiunge
        cursor.execute("INSERT INTO points (user_id, points) VALUES (?, ?)", (user_id, amount))

    conn.commit()
    conn.close()

def get_points(user_id):
    """Recupera i punti di un utente da SQLite."""
    conn = sqlite3.connect("points_database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT points FROM points WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else 0  # ✅ Ritorna 0 se l'utente non ha punti

def get_all_points():
    """Recupera tutti gli utenti e i loro punti dal database."""
    conn = sqlite3.connect("points_database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, points FROM points ORDER BY points DESC")
    result = cursor.fetchall()

    conn.close()
    return {user_id: points for user_id, points in result}  # ✅ Ritorna un dizionario di utenti e punti

# Comandi bot
@bot.tree.command(name="addpoints", description="Add points to a user by ID")
@discord.app_commands.default_permissions(manage_roles=True)
async def addpoints(interaction: discord.Interaction, user_id: str, amount: int):
    """Aggiunge punti a un utente usando solo il suo ID, anche se non è nel server."""
    try:
        user_id = int(user_id)
        add_points(user_id, amount)

        embed = discord.Embed(
            title=f"{bot.user.name} - Points System",
            description=f"Added **{amount}** points to `{user_id}`.\nNew balance: **{get_points(user_id)}**.",
            color=discord.Color.from_rgb(230, 230, 230)
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=False)

    except ValueError:
        embed = discord.Embed(
            title=f"{bot.user.name} - Error",
            description="Invalid user ID format. Please provide a numeric ID.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removepoints", description="Remove points from a user by ID")
@discord.app_commands.default_permissions(manage_roles=True)
async def removepoints(interaction: discord.Interaction, user_id: str, amount: int):
    """Rimuove punti a un utente usando solo il suo ID, senza dipendere dal server."""
    try:
        user_id = int(user_id)
        current_points = get_points(user_id)

        if current_points == 0:
            embed = discord.Embed(
                title=f"{bot.user.name} - Points System",
                description=f"User `{user_id}` has no points.",
                color=discord.Color.from_rgb(230, 230, 230)
            )
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        add_points(user_id, -amount)

        embed = discord.Embed(
            title=f"{bot.user.name}",
            description=f"Removed **{amount}** points from `{user_id}`.\nNew balance: **{get_points(user_id)}**.",
            color=discord.Color.from_rgb(230, 230, 230)
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=False)

    except ValueError:
        embed = discord.Embed(
            title=f"{bot.user.name} - Error",
            description="Invalid user ID format. Please provide a numeric ID.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="leaderboard", description="Show the leaderboard with pages")
async def leaderboard(interaction: discord.Interaction):
    """Mostra la classifica con pagine e bottoni in un embed elegante."""
    sorted_points = sorted(get_all_points().items(), key=lambda x: x[1], reverse=True)

    if not sorted_points:
        embed = discord.Embed(
            title=f"{bot.user.name} - Leaderboard",
            description="No points have been assigned yet!",
            color=discord.Color.from_rgb(230, 230, 230)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(title="Points Leaderboard", color=discord.Color.from_rgb(230, 230, 230))
    for i, (user_id, score) in enumerate(sorted_points[:50], start=1):
        embed.add_field(name=f"{i}. `{user_id}`", value=f"{score} points", inline=False)

    await interaction.response.send_message(embed=embed)

# Avvia il bot  
bot.run("MTM3OTUwOTA2OTM2NjE2NTYwNQ.G0AVWp.5muT_hzXgWQ_vHYog9J17vLMap3ynFCdONJbIo")  # ⚠️ Usa il token corretto!