import discord
from discord.ext import commands
import json
import os

# ───────── CONFIG ─────────
TOKEN = os.getenv("TOKEN")
PREFIX = "&"
CREATOR_PP_ROLE_ID = 1467009008417247314

# ───────── BOT ─────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ───────── GRADES ─────────
GRADES = {
    "Créateur++": 6,
    "Créateur": 5,
    "Sys": 4,
    "Owner": 3,
    "Staff": 2,
    "User": 1
}

# ───────── FILES ─────────
BL_FILE = "blacklist.json"
LOGS_FILE = "logs_channel.json"

def load_blacklist():
    if not os.path.exists(BL_FILE):
        with open(BL_FILE, "w") as f:
            json.dump({}, f)
    with open(BL_FILE, "r") as f:
        return json.load(f)

def save_blacklist(data):
    with open(BL_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_logs_channel():
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "w") as f:
            json.dump({}, f)
    with open(LOGS_FILE, "r") as f:
        return json.load(f)

def save_logs_channel(data):
    with open(LOGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user_grade(member: discord.Member):
    for role in member.roles:
        if role.id == CREATOR_PP_ROLE_ID:
            return "Créateur++"
        if role.name in GRADES:
            return role.name
    return "User"

def enforce_hardlock(member, stored_grade):
    real_grade = get_user_grade(member)
    if real_grade == "Créateur++":
        return "Créateur++"
    if GRADES.get(stored_grade, 0) > GRADES.get(real_grade, 0):
        return real_grade
    return stored_grade

async def send_log(ctx, action: str, target: discord.Member, reason: str = None, executor: discord.Member = None):
    logs_data = load_logs_channel()
    guild_id = str(ctx.guild.id)
    
    if guild_id not in logs_data:
        return
    
    channel_id = logs_data[guild_id]
    channel = bot.get_channel(channel_id)
    
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except:
            return
    
    color = 0xFF0000 if action == "BLACKLIST" else 0x00FF00
    embed = discord.Embed(
        title=f"📝 LOGS - {action}",
        color=color,
        timestamp=ctx.message.created_at
    )
    
    if executor:
        embed.add_field(name="👤 Exécuteur", value=executor.mention, inline=True)
        embed.add_field(name="🆔 ID Exécuteur", value=executor.id, inline=True)
    
    embed.add_field(name="🎯 Cible", value=target.mention, inline=True)
    embed.add_field(name="🆔 ID Cible", value=target.id, inline=True)
    
    if action == "BLACKLIST":
        embed.add_field(name="📌 Raison", value=reason or "Non spécifiée", inline=False)
    
    embed.set_footer(text=f"Action effectuée")
    
    try:
        await channel.send(embed=embed)
    except:
        pass

# ───────── EVENTS ─────────
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

# ───────── COMMANDES ─────────
@bot.command()
async def setlogs(ctx, channel: discord.TextChannel = None):
    executor_grade = get_user_grade(ctx.author)
    
    if executor_grade != "Créateur++":
        await ctx.send("🚫 **Commande réservée aux Créateur++ uniquement.**")
        return
    
    if not channel:
        logs_data = load_logs_channel()
        guild_id = str(ctx.guild.id)
        
        if guild_id in logs_data:
            channel_id = logs_data[guild_id]
            channel_mention = f"<#{channel_id}>"
            await ctx.send(f"📊 **Salon de logs actuel** : {channel_mention}\nUtilise `&setlogs #salon` pour le changer.")
        else:
            await ctx.send("ℹ️ Aucun salon de logs configuré.\nUtilise `&setlogs #salon` pour en configurer un.")
        return
    
    logs_data = load_logs_channel()
    logs_data[str(ctx.guild.id)] = channel.id
    save_logs_channel(logs_data)
    
    log_embed = discord.Embed(
        title="⚙️ Configuration des logs",
        color=0x5865F2,
        timestamp=ctx.message.created_at
    )
    log_embed.add_field(name="Action", value="Salon de logs configuré", inline=False)
    log_embed.add_field(name="👤 Configuré par", value=ctx.author.mention, inline=True)
    log_embed.add_field(name="🆔 ID Configurateur", value=ctx.author.id, inline=True)
    log_embed.add_field(name="📌 Salon configuré", value=channel.mention, inline=False)
    log_embed.set_footer(text="Configuration système")
    
    await ctx.send(f"✅ **Salon de logs configuré** : {channel.mention}\nToutes les actions de blacklist seront loggées ici.")
    
    try:
        await channel.send(embed=log_embed)
    except:
        pass

@bot.command()
async def bl(ctx, member: discord.Member, *, reason: str):
    executor_grade = get_user_grade(ctx.author)
    target_grade = get_user_grade(member)

    if target_grade == "Créateur++":
        await ctx.send("🚫 Impossible de blacklist un **Créateur++**.")
        return

    if GRADES[executor_grade] <= GRADES[target_grade]:
        await ctx.send("🚫 Tu ne peux pas blacklist quelqu'un de ton niveau ou supérieur.")
        return

    bl_data = load_blacklist()
    bl_data[str(member.id)] = {
        "grade": target_grade,
        "reason": reason,
        "by": ctx.author.id
    }

    save_blacklist(bl_data)
    await ctx.send(f"⛔ **{member}** a été blacklist.\n📌 Raison : {reason}")
    await send_log(ctx, "BLACKLIST", member, reason, ctx.author)

@bot.command()
async def unbl(ctx, member: discord.Member):
    bl_data = load_blacklist()
    uid = str(member.id)

    if uid not in bl_data:
        await ctx.send("❌ Cet utilisateur n'est pas blacklist.")
        return

    executor_grade = get_user_grade(ctx.author)
    stored_grade = bl_data[uid]["grade"]
    real_grade = enforce_hardlock(member, stored_grade)

    if real_grade == "Créateur++" and executor_grade != "Créateur++":
        await ctx.send("🚫 Seul un **Créateur++** peut unbl un autre Créateur++.")
        return

    del bl_data[uid]
    save_blacklist(bl_data)
    await ctx.send(f"✅ **{member}** a été retiré de la blacklist.")
    await send_log(ctx, "UNBLACKLIST", member, executor=ctx.author)

@bot.command()
async def unblall(ctx):
    executor_grade = get_user_grade(ctx.author)

    if executor_grade != "Créateur++":
        await ctx.send("🚫 Cette commande est réservée aux **Créateur++**.")
        return

    bl_data = load_blacklist()
    count = len(bl_data)
    
    logs_data = load_logs_channel()
    guild_id = str(ctx.guild.id)
    
    if guild_id in logs_data:
        channel_id = logs_data[guild_id]
        channel = bot.get_channel(channel_id)
        
        if channel:
            embed = discord.Embed(
                title="📝 LOGS - UNBLACKLIST ALL",
                color=0x00FF00,
                timestamp=ctx.message.created_at
            )
            embed.add_field(name="👤 Exécuteur", value=ctx.author.mention, inline=True)
            embed.add_field(name="🆔 ID Exécuteur", value=ctx.author.id, inline=True)
            embed.add_field(name="🎯 Nombre d'utilisateurs", value=str(count), inline=False)
            embed.set_footer(text="Action effectuée")
            
            try:
                await channel.send(embed=embed)
            except:
                pass
    
    bl_data.clear()
    save_blacklist(bl_data)
    await ctx.send(f"🧹 **{count} utilisateurs** ont été unblacklist.")

@bot.command()
async def blinfo(ctx, member: discord.Member):
    bl_data = load_blacklist()
    uid = str(member.id)

    if uid not in bl_data:
        await ctx.send("❌ Cet utilisateur n'est pas blacklist.")
        return

    data = bl_data[uid]
    embed = discord.Embed(
        title="📄 Blacklist Info",
        color=0xFF0000
    )
    embed.add_field(name="Utilisateur", value=member.mention)
    embed.add_field(name="Grade", value=data["grade"])
    embed.add_field(name="Raison", value=data["reason"])
    embed.add_field(name="Blacklist par", value=f"<@{data['by']}>")
    await ctx.send(embed=embed)

@bot.command()
async def bllist(ctx):
    bl_data = load_blacklist()

    if not bl_data:
        await ctx.send("✅ Aucun utilisateur blacklist.")
        return

    desc = ""
    for uid, data in bl_data.items():
        desc += f"<@{uid}> — **{data['grade']}**\n"

    embed = discord.Embed(
        title="📛 Liste des blacklist",
        description=desc,
        color=0x2F3136
    )
    await ctx.send(embed=embed)

@bot.command()
async def grades(ctx):
    embed = discord.Embed(title="📊 Hiérarchie des grades", color=0x000000)
    embed.add_field(name="👑 Créateur++", value="• Grade absolu\n• ❌ Impossible à BL\n• ✅ Peut unbl un Créateur++\n• 🔒 Hard-lock\n• ⚙️ Peut configurer les logs", inline=False)
    embed.add_field(name="⭐ Créateur", value="• Modération avancée\n• ❌ Aucun pouvoir sur Créateur++\n• ❌ Ne peut pas configurer les logs", inline=False)
    embed.add_field(name="🛠️ Sys", value="• Gestion serveur\n• ❌ Ne peut pas configurer les logs", inline=False)
    embed.add_field(name="🔑 Owner", value="• Modération standard", inline=False)
    embed.add_field(name="👮 Staff", value="• Modération basique", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def helpbot(ctx):
    embed = discord.Embed(title="🆘 Commandes du Bot", color=0x7289DA)
    embed.add_field(name="🔨 Modération", value="`&bl @user raison` - Blacklist\n`&unbl @user` - Retirer blacklist\n`&unblall` - Tout retirer (Créateur++)\n`&bllist` - Liste des blacklist\n`&blinfo @user` - Infos blacklist", inline=False)
    embed.add_field(name="⚙️ Configuration", value="`&setlogs #salon` - Configurer logs (Créateur++)\n`&grades` - Voir la hiérarchie", inline=False)
    embed.set_footer(text=f"Préfixe: {PREFIX}")
    await ctx.send(embed=embed)

# ───────── RUN ─────────
if __name__ == "__main__":
    bot.run(TOKEN)
