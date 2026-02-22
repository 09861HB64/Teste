import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import json
import datetime
from threading import Thread
from flask import Flask, jsonify, render_template_string, request
import time

# ============================================================
# CONFIGURAÇÕES
# ============================================================
TOKEN = os.environ.get("DISCORD_TOKEN_BOT1", "TOKEN_BOT1_AQUI")
BOT_START_TIME = time.time()
bot_running = True

# Canais que NÃO serão deletados no /create
PROTECTED_CHANNEL_IDS = [
    1472068898567491597,
    1473485452768972933,
]

# ============================================================
# FLASK - PAINEL WEB
# ============================================================
app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Bot 1 Dashboard</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body { background:#0d0d0d; color:#e0e0e0; font-family:'Segoe UI',sans-serif; min-height:100vh; display:flex; flex-direction:column; align-items:center; }
    header { width:100%; background:linear-gradient(90deg,#5865F2,#7289da); padding:22px 40px; display:flex; align-items:center; gap:16px; box-shadow:0 4px 20px #0008; }
    header h1 { font-size:1.7rem; font-weight:700; color:#fff; letter-spacing:1px; }
    .badge { background:#23272a; color:#43b581; border-radius:20px; padding:4px 14px; font-size:.85rem; font-weight:600; border:1.5px solid #43b581; }
    .badge.offline { color:#f04747; border-color:#f04747; }
    .container { width:100%; max-width:900px; padding:36px 20px; display:flex; flex-direction:column; gap:24px; }
    .card { background:#1a1a2e; border-radius:14px; padding:28px 32px; box-shadow:0 2px 16px #0006; border:1px solid #2a2a4a; }
    .card h2 { font-size:1.1rem; color:#7289da; margin-bottom:18px; display:flex; align-items:center; gap:8px; }
    .stat-row { display:flex; flex-wrap:wrap; gap:18px; }
    .stat { flex:1; min-width:150px; background:#16213e; border-radius:10px; padding:18px 20px; text-align:center; border:1px solid #2a2a5a; }
    .stat .val { font-size:2rem; font-weight:700; color:#5865F2; }
    .stat .label { font-size:.8rem; color:#aaa; margin-top:4px; }
    .btn { display:inline-block; padding:11px 28px; border-radius:8px; font-size:.95rem; font-weight:600; cursor:pointer; border:none; transition:.2s; }
    .btn-green { background:#43b581; color:#fff; }
    .btn-red { background:#f04747; color:#fff; }
    .btn-blue { background:#5865F2; color:#fff; }
    .actions { display:flex; gap:14px; flex-wrap:wrap; }
    .log-box { background:#0d0d0d; border-radius:8px; padding:14px 18px; font-family:monospace; font-size:.82rem; color:#43b581; max-height:200px; overflow-y:auto; border:1px solid #2a2a4a; }
    .status-dot { width:10px; height:10px; border-radius:50%; background:#43b581; display:inline-block; margin-right:6px; animation:pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
    footer { margin-top:auto; padding:18px; color:#555; font-size:.8rem; }
  </style>
</head>
<body>
  <header>
    <div class="status-dot" id="sdot"></div>
    <h1>🤖 Discord Bot 1 — Dashboard</h1>
    <span class="badge" id="statusBadge">ONLINE</span>
  </header>
  <div class="container">
    <div class="card">
      <h2>📊 Estatísticas</h2>
      <div class="stat-row">
        <div class="stat"><div class="val" id="uptime">--</div><div class="label">Uptime</div></div>
        <div class="stat"><div class="val" id="guilds">--</div><div class="label">Servidores</div></div>
        <div class="stat"><div class="val" id="users">--</div><div class="label">Usuários</div></div>
        <div class="stat"><div class="val" id="latency">--</div><div class="label">Latência (ms)</div></div>
      </div>
    </div>
    <div class="card">
      <h2>⚙️ Controles</h2>
      <div class="actions">
        <button class="btn btn-blue" onclick="fetchStats()">🔄 Atualizar</button>
      </div>
    </div>
    <div class="card">
      <h2>📜 Log de Atividade</h2>
      <div class="log-box" id="logBox">Aguardando logs...</div>
    </div>
  </div>
  <footer>Bot 1 Dashboard &copy; 2025</footer>
  <script>
    async function fetchStats() {
      try {
        const r = await fetch('/api/stats');
        const d = await r.json();
        document.getElementById('uptime').innerText = d.uptime;
        document.getElementById('guilds').innerText = d.guilds;
        document.getElementById('users').innerText = d.users;
        document.getElementById('latency').innerText = d.latency;
      } catch(e) {}
    }
    fetchStats();
    setInterval(fetchStats, 30000);
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_DASHBOARD)

@app.route("/ping")
def ping():
    return "OK", 200

@app.route("/api/stats")
def api_stats():
    uptime_sec = int(time.time() - BOT_START_TIME)
    h = uptime_sec // 3600
    m = (uptime_sec % 3600) // 60
    s = uptime_sec % 60
    uptime_str = f"{h}h {m}m {s}s"
    try:
        guilds = len(bot.guilds)
        users = sum(g.member_count or 0 for g in bot.guilds)
        latency = round(bot.latency * 1000)
        status = "online"
    except Exception:
        guilds = 0; users = 0; latency = 0; status = "offline"
    return jsonify({"status": status, "uptime": uptime_str, "guilds": guilds, "users": users, "latency": latency})

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ============================================================
# BOT DISCORD
# ============================================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

guild_data = {}

def get_gd(guild_id):
    if guild_id not in guild_data:
        guild_data[guild_id] = {
            "support_role_id": None,
            "support_users": [],
            "tickets": {},
            "member_msg_id": None,
            "member_ch_id": None,
            "invite_msg_id": None,
            "invite_ch_id": None,
        }
    return guild_data[guild_id]

# ============================================================
# EVENTOS
# ============================================================
@bot.event
async def on_ready():
    print(f"✅ Bot 1 online como {bot.user}")
    await tree.sync()
    auto_close_tickets.start()
    update_member_count.start()
    print("✅ Tasks iniciadas")

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    # Auto role Membro
    member_role = discord.utils.get(guild.roles, name="👤 Membro")
    if member_role:
        try:
            await member.add_roles(member_role)
        except Exception:
            pass
    # Boas-vindas
    welcome_ch = discord.utils.get(guild.text_channels, name="「👋」boas-vindas")
    if welcome_ch:
        embed = discord.Embed(
            title=f"✨ Bem-vindo(a) ao {guild.name}!",
            description=(
                f"Olá {member.mention}, seja muito bem-vindo(a)!\n\n"
                f"🎉 Você é o **membro #{guild.member_count}** do servidor!\n"
                f"📜 Leia as regras em `「📜」regras`\n"
                f"💬 Bom divertimento!"
            ),
            color=0x43b581,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if guild.icon:
            embed.set_image(url=guild.icon.url)
        embed.set_footer(text=f"{guild.name} • Bem-vindo!")
        await welcome_ch.send(embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    goodbye_ch = discord.utils.get(guild.text_channels, name="「👋」boas-vindas")
    if goodbye_ch:
        embed = discord.Embed(
            title=f"👋 {member.display_name} saiu...",
            description=(
                f"{member.mention} deixou o servidor.\n\n"
                f"😢 Sentiremos sua falta!\n"
                f"👥 Agora somos **{guild.member_count}** membros."
            ),
            color=0xf04747,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{guild.name} • Até logo!")
        await goodbye_ch.send(embed=embed)

# ============================================================
# TASK: Atualizar contagem de membros a cada 1 hora
# ============================================================
@tasks.loop(hours=1)
async def update_member_count():
    for guild_id, gd in guild_data.items():
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
        ch_id = gd.get("member_ch_id")
        msg_id = gd.get("member_msg_id")
        if not ch_id or not msg_id:
            continue
        ch = guild.get_channel(ch_id)
        if not ch:
            continue
        try:
            msg = await ch.fetch_message(msg_id)
            embed = discord.Embed(
                title=f"👥 {guild.member_count} Membros",
                description="Contagem atualizada a cada hora automaticamente!",
                color=0x43b581,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_footer(text="Última atualização")
            await msg.edit(embed=embed)
        except Exception as e:
            print(f"Erro ao atualizar membros: {e}")

# ============================================================
# TASK: Fechar tickets automático
# ============================================================
@tasks.loop(minutes=5)
async def auto_close_tickets():
    now = datetime.datetime.utcnow()
    for guild_id, gd in guild_data.items():
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
        to_close = []
        for ch_id, tinfo in list(gd["tickets"].items()):
            ch = guild.get_channel(ch_id)
            if not ch:
                to_close.append(ch_id)
                continue
            opened_at = tinfo.get("opened_at")
            assumed = tinfo.get("assumed", False)
            if not opened_at:
                continue
            delta = (now - opened_at).total_seconds()
            if not assumed and delta > 43200 and not tinfo.get("warned_12h"):
                tinfo["warned_12h"] = True
                log_ch = discord.utils.get(guild.text_channels, name="「📋」logs-tickets")
                if log_ch:
                    embed = discord.Embed(
                        title="⚠️ Ticket sem atendimento",
                        description=f"O ticket {ch.mention} está aberto há mais de 12h sem admin assumir.",
                        color=0xffa500,
                        timestamp=now
                    )
                    await log_ch.send(embed=embed)
            if assumed and delta > 68400 and not tinfo.get("auto_closing"):
                tinfo["auto_closing"] = True
                await ch.send("⏰ Ticket fechando automaticamente em 6 segundos...")
                await asyncio.sleep(6)
                await _close_ticket_channel(guild, ch, tinfo, "Auto-close por inatividade (19h)")
                to_close.append(ch_id)
        for ch_id in to_close:
            gd["tickets"].pop(ch_id, None)

async def _close_ticket_channel(guild, channel, tinfo, motivo):
    log_ch = discord.utils.get(guild.text_channels, name="「📋」logs-tickets")
    opener_id = tinfo.get("opener_id")
    opener = guild.get_member(opener_id) if opener_id else None
    embed = discord.Embed(
        title="🔒 Ticket Fechado",
        description=f"**Ticket:** {channel.name}\n**Motivo:** {motivo}\n**Aberto por:** {opener.mention if opener else 'Desconhecido'}",
        color=0xf04747,
        timestamp=datetime.datetime.utcnow()
    )
    if log_ch:
        await log_ch.send(embed=embed)
    if opener:
        try:
            await opener.send(embed=embed)
        except Exception:
            pass
    if guild.owner:
        try:
            await guild.owner.send(embed=embed)
        except Exception:
            pass
    try:
        await channel.delete(reason=motivo)
    except Exception:
        pass

# ============================================================
# COMANDO /create — APAGA TUDO E RECRIA
# ============================================================
@tree.command(name="create", description="Apaga todos os canais e recria o servidor completo (apenas dono)")
async def create_command(interaction: discord.Interaction):
    guild = interaction.guild
    if interaction.user.id != guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono do servidor** pode usar este comando!", ephemeral=True)
        return

    await interaction.response.send_message("⚙️ Iniciando configuração completa... Isso pode levar alguns minutos!", ephemeral=True)

    # ── DELETAR todos os canais e categorias EXCETO os protegidos ──
    for channel in list(guild.channels):
        if channel.id in PROTECTED_CHANNEL_IDS:
            continue
        try:
            await channel.delete(reason="/create: recriando servidor")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Erro ao deletar {channel.name}: {e}")

    # ── DELETAR cargos antigos (exceto @everyone e cargos do bot) ──
    roles_to_keep = {"@everyone"}
    for role in list(guild.roles):
        if role.name in roles_to_keep or role.managed or role.is_bot_managed():
            continue
        if role >= guild.me.top_role:
            continue
        try:
            await role.delete(reason="/create: recriando cargos")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"Erro ao deletar cargo {role.name}: {e}")

    # ── CRIAR CARGOS ──
    # @everyone sem permissões
    await guild.default_role.edit(permissions=discord.Permissions(read_messages=False, send_messages=False))

    # 👑 Owner
    owner_role = await guild.create_role(
        name="👑 Owner",
        color=discord.Color.gold(),
        permissions=discord.Permissions(administrator=True),
        hoist=True, reason="Setup automático"
    )
    # 🛡️ Admin
    admin_role = await guild.create_role(
        name="🛡️ Admin",
        color=discord.Color.red(),
        permissions=discord.Permissions(administrator=True),
        hoist=True, reason="Setup automático"
    )
    # ⚙️ Moderador
    mod_role = await guild.create_role(
        name="⚙️ Moderador",
        color=discord.Color.orange(),
        permissions=discord.Permissions(
            manage_messages=True, kick_members=True, ban_members=True,
            read_messages=True, send_messages=True, manage_channels=True,
            read_message_history=True, mute_members=True, deafen_members=True,
            move_members=True, use_application_commands=True
        ),
        hoist=True, reason="Setup automático"
    )
    # 🎫 Support
    support_role = await guild.create_role(
        name="🎫 Support",
        color=discord.Color.green(),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, manage_channels=True,
            read_message_history=True, attach_files=True, embed_links=True,
            manage_messages=True, use_application_commands=True
        ),
        hoist=True, reason="Setup automático"
    )
    # 📢 Divulgador
    divulgador_role = await guild.create_role(
        name="📢 Divulgador",
        color=discord.Color.purple(),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True,
            mention_everyone=True
        ),
        hoist=True, reason="Setup automático"
    )
    # 🛒 Comprador
    comprador_role = await guild.create_role(
        name="🛒 Comprador",
        color=discord.Color.from_str("#00b4d8"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True,
            add_reactions=True, use_external_emojis=True, use_external_stickers=True
        ),
        hoist=True, reason="Setup automático"
    )
    # 💰 Vendedor
    vendedor_role = await guild.create_role(
        name="💰 Vendedor",
        color=discord.Color.from_str("#ffd166"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True,
            add_reactions=True, use_external_emojis=True
        ),
        hoist=True, reason="Setup automático"
    )
    # 📊 User Logs
    userlogs_role = await guild.create_role(
        name="📊 User Logs",
        color=discord.Color.from_str("#90e0ef"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            read_message_history=True, add_reactions=True, use_application_commands=True
        ),
        hoist=False, reason="Setup automático"
    )
    # 🤝 Parceiro
    parceiro_role = await guild.create_role(
        name="🤝 Parceiro",
        color=discord.Color.from_str("#a8dadc"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            read_message_history=True, add_reactions=True
        ),
        hoist=True, reason="Setup automático"
    )
    # 🎁 VIP
    vip_role = await guild.create_role(
        name="🎁 VIP",
        color=discord.Color.from_str("#e63946"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True,
            add_reactions=True, use_external_emojis=True, use_external_stickers=True
        ),
        hoist=True, reason="Setup automático"
    )
    # 👤 Membro
    member_role = await guild.create_role(
        name="👤 Membro",
        color=discord.Color.from_str("#7289da"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, read_message_history=True,
            attach_files=True, embed_links=True, add_reactions=True,
            use_application_commands=True, use_external_emojis=True, use_external_stickers=True
        ),
        reason="Setup automático"
    )

    # Dar cargo Owner + Support ao dono
    try:
        owner_member = guild.get_member(guild.owner_id)
        if owner_member:
            await owner_member.add_roles(owner_role, support_role)
    except Exception:
        pass

    gd = get_gd(guild.id)
    gd["support_role_id"] = support_role.id

    # ── HELPERS DE PERMISSÃO ──
    def pub_ow():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

    def chat_ow():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True, add_reactions=True,
                use_external_emojis=True, use_external_stickers=True
            ),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }

    def logs_ow():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

    def userlogs_ow():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=False),
            userlogs_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, read_message_history=True,
                add_reactions=True, use_external_emojis=True, use_external_stickers=True
            ),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

    # ── CATEGORIA: INFORMAÇÕES ──
    cat_info = await guild.create_category("┏━━ 📌 INFORMAÇÕES ━━┓", position=0)
    ch_invites = await guild.create_text_channel("「🔗」convite", category=cat_info, overwrites=pub_ow())
    ch_members = await guild.create_text_channel("「👥」membros", category=cat_info, overwrites=pub_ow())
    ch_welcome = await guild.create_text_channel("「👋」boas-vindas", category=cat_info, overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    })
    ch_rules = await guild.create_text_channel("「📜」regras", category=cat_info, overwrites=pub_ow())
    ch_avisos = await guild.create_text_channel("「📣」avisos", category=cat_info, overwrites=pub_ow())
    ch_parcerias = await guild.create_text_channel("「🤝」parcerias", category=cat_info, overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        parceiro_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    })

    # ── CATEGORIA: CHAT ──
    cat_chat = await guild.create_category("┣━━ 💬 CHAT ━━┫")
    await guild.create_text_channel("「💬」geral", category=cat_chat, overwrites=chat_ow())
    await guild.create_text_channel("「😂」memes", category=cat_chat, overwrites=chat_ow())
    await guild.create_text_channel("「🎮」jogos", category=cat_chat, overwrites=chat_ow())
    await guild.create_text_channel("「🤣」off-topic", category=cat_chat, overwrites=chat_ow())

    # ── CATEGORIA: MÍDIA ──
    cat_media = await guild.create_category("┣━━ 📸 MÍDIA ━━┫")
    media_ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, use_external_emojis=True, use_external_stickers=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    await guild.create_text_channel("「📸」fotos", category=cat_media, overwrites=media_ow)
    await guild.create_text_channel("「🎬」vídeos", category=cat_media, overwrites=media_ow)
    await guild.create_text_channel("「🎵」músicas", category=cat_media, overwrites=media_ow)

    # ── CATEGORIA: COMANDOS ──
    cat_cmds = await guild.create_category("┣━━ ⚡ COMANDOS ━━┫")
    cmd_ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, use_application_commands=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    await guild.create_text_channel("「⚡」bot-cmds", category=cat_cmds, overwrites=cmd_ow)
    ch_hits = await guild.create_text_channel("「🏆」hits", category=cat_cmds, overwrites=pub_ow())
    ch_tutorial = await guild.create_text_channel("「📖」tutorial-key", category=cat_cmds, overwrites=pub_ow())

    # ── CATEGORIA: LOJA ──
    cat_loja = await guild.create_category("┣━━ 🛒 LOJA ━━┫")
    loja_ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True),
        comprador_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        vendedor_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    await guild.create_text_channel("「🛒」produtos", category=cat_loja, overwrites=loja_ow)
    await guild.create_text_channel("「💳」pagamentos", category=cat_loja, overwrites=loja_ow)
    await guild.create_text_channel("「⭐」avaliações", category=cat_loja, overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, add_reactions=True),
        comprador_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    })

    # ── CATEGORIA: SUPORTE ──
    cat_support = await guild.create_category("┣━━ 🎫 SUPORTE ━━┫")
    support_ticket_ow = pub_ow()
    ch_tickets = await guild.create_text_channel("「🎫」tickets", category=cat_support, overwrites=support_ticket_ow)

    # ── CATEGORIA: USER LOGS ──
    cat_ulogs = await guild.create_category("┣━━ 📊 USER LOGS ━━┫")
    ch_ulogs = await guild.create_text_channel("「📊」user-logs", category=cat_ulogs, overwrites=userlogs_ow())
    await guild.create_text_channel("「📝」criar-log", category=cat_ulogs, overwrites=chat_ow())

    # ── CATEGORIA: LOGS ADMIN ──
    cat_logs = await guild.create_category("┗━━ 📋 LOGS ━━┛")
    await guild.create_text_channel("「📋」logs-tickets", category=cat_logs, overwrites=logs_ow())
    await guild.create_text_channel("「🔍」logs-gerais", category=cat_logs, overwrites=logs_ow())
    await guild.create_text_channel("「👥」logs-membros", category=cat_logs, overwrites=logs_ow())
    await guild.create_text_channel("「💬」logs-mensagens", category=cat_logs, overwrites=logs_ow())

    # ── CONTEÚDO DOS CANAIS ──

    # Regras
    embed_rules = discord.Embed(
        title="📜 Regras do Servidor",
        description=(
            "**Leia atentamente antes de participar!**\n\n"
            "**1.** Respeite todos os membros.\n"
            "**2.** Sem spam ou flood nos canais.\n"
            "**3.** Sem conteúdo NSFW ou ofensivo.\n"
            "**4.** Siga as diretrizes do Discord.\n"
            "**5.** Sem divulgação não autorizada.\n"
            "**6.** Ouça os admins e moderadores.\n"
            "**7.** Sem racismo, homofobia ou preconceito.\n"
            "**8.** Use os canais para seus propósitos.\n\n"
            "⚠️ O descumprimento resultará em punição ou ban!"
        ),
        color=0x5865F2
    )
    embed_rules.set_footer(text=f"{guild.name} • Regras")
    await ch_rules.send(embed=embed_rules)

    # Avisos
    embed_avisos = discord.Embed(
        title="📣 Canal de Avisos",
        description="Fique atento aqui para os avisos importantes do servidor!\n\nSó a equipe pode enviar mensagens neste canal.",
        color=0xffa500
    )
    await ch_avisos.send(embed=embed_avisos)

    # Parcerias
    embed_parcerias = discord.Embed(
        title="🤝 Parcerias",
        description=(
            "**Quer fazer parceria conosco?**\n\n"
            "Abra um ticket no canal `「🎫」tickets` com o tipo **Parceria** e apresente seu servidor!\n\n"
            "✅ Requisitos mínimos:\n"
            "• Servidor ativo\n"
            "• Mínimo de 50 membros\n"
            "• Conteúdo relacionado\n"
        ),
        color=0xa8dadc
    )
    await ch_parcerias.send(embed=embed_parcerias)

    # Convite
    invite = await ch_invites.create_invite(max_age=0, max_uses=0)
    embed_inv = discord.Embed(
        title="🔗 Convide seus amigos!",
        description=f"**Link do servidor:**\n```{invite.url}```\nCompartilhe e ajude a comunidade a crescer! 💜",
        color=0x5865F2
    )
    embed_inv.set_footer(text=f"{guild.name}")
    inv_msg = await ch_invites.send(embed=embed_inv)
    gd["invite_ch_id"] = ch_invites.id
    gd["invite_msg_id"] = inv_msg.id

    # Membros
    embed_mem = discord.Embed(
        title=f"👥 {guild.member_count} Membros",
        description="A contagem de membros é atualizada automaticamente a cada hora!",
        color=0x43b581,
        timestamp=datetime.datetime.utcnow()
    )
    embed_mem.set_footer(text="Última atualização")
    mem_msg = await ch_members.send(embed=embed_mem)
    gd["member_ch_id"] = ch_members.id
    gd["member_msg_id"] = mem_msg.id

    # Tutorial Key
    embed_tut = discord.Embed(
        title="📖 Tutorial — Como Gerar sua Key",
        description=(
            "**Passo 1:** Vá até `「⚡」bot-cmds`\n"
            "**Passo 2:** Use `/gerar_key`\n"
            "**Passo 3:** Copie e guarde sua key em local seguro\n"
            "**Passo 4:** Use para acessar recursos exclusivos\n\n"
            "⚠️ Cada usuário gera apenas **1 key**.\n"
            "📩 Dúvidas? Abra um ticket!"
        ),
        color=0x7289da
    )
    await ch_tutorial.send(embed=embed_tut)

    # Hits
    embed_hits = discord.Embed(
        title="🏆 Hall of Fame — Hits",
        description="Aqui ficam os maiores hits e conquistas!\n\nUse `/hit` para registrar o seu! 🎯",
        color=0xffd700
    )
    await ch_hits.send(embed=embed_hits)

    # User Logs
    embed_ulogs = discord.Embed(
        title="📊 User Logs",
        description=(
            "Este é o canal de User Logs!\n\n"
            "Apenas usuários com o cargo **📊 User Logs** podem ver e interagir aqui.\n"
            "Configure o Bot 2 com `/add_logs` para liberar acesso."
        ),
        color=0x90e0ef
    )
    await ch_ulogs.send(embed=embed_ulogs)

    # Painel de Tickets
    embed_ticket = discord.Embed(
        title="🎫 Central de Suporte",
        description=(
            "Bem-vindo à Central de Suporte!\n\n"
            "Clique em um dos botões abaixo:\n\n"
            "🟢 **Abrir Ticket** — Fale com a equipe\n"
            "🤝 **Parceria** — Proposta de parceria\n"
            "❓ **Dúvidas** — Tire suas dúvidas\n"
            "💳 **Pagamento** — Formas de pagamento\n"
            "📝 **Criar Log** — Crie sua log pessoal\n\n"
            "⏰ Atendimento **24/7**"
        ),
        color=0x5865F2
    )
    embed_ticket.set_footer(text=f"{guild.name} — Suporte 24/7")
    if guild.icon:
        embed_ticket.set_thumbnail(url=guild.icon.url)

    bot.add_view(TicketPanelView())
    await ch_tickets.send(embed=embed_ticket, view=TicketPanelView())

    await interaction.followup.send(
        "✅ **Servidor configurado com sucesso!**\n"
        "Todos os canais e cargos foram criados!\n"
        "Canais protegidos foram mantidos.\n"
        "Use `/suport_cargo` e `/add_usuario` para gerenciar a equipe. 🎉",
        ephemeral=True
    )

# ============================================================
# VIEWS — PAINEL DE TICKETS
# ============================================================
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket", emoji="🟢", style=discord.ButtonStyle.green, custom_id="ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "ticket")

    @discord.ui.button(label="Parceria", emoji="🤝", style=discord.ButtonStyle.blurple, custom_id="ticket_parceria")
    async def parceria(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "parceria")

    @discord.ui.button(label="Dúvidas", emoji="❓", style=discord.ButtonStyle.secondary, custom_id="ticket_duvidas")
    async def duvidas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "duvidas")

    @discord.ui.button(label="Pagamento", emoji="💳", style=discord.ButtonStyle.secondary, custom_id="ticket_pagamento")
    async def pagamento(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "pagamento")

    @discord.ui.button(label="Criar Log", emoji="📝", style=discord.ButtonStyle.secondary, custom_id="ticket_log")
    async def criar_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "criar-log")


async def create_ticket(interaction: discord.Interaction, tipo: str):
    guild = interaction.guild
    user = interaction.user
    gd = get_gd(guild.id)

    for ch_id, tinfo in gd["tickets"].items():
        if tinfo.get("opener_id") == user.id:
            await interaction.response.send_message("❌ Você já possui um ticket aberto!", ephemeral=True)
            return

    support_role = guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
    owner_role = discord.utils.get(guild.roles, name="👑 Owner")
    admin_role = discord.utils.get(guild.roles, name="🛡️ Admin")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
    }
    if guild.owner:
        overwrites[guild.owner] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if owner_role:
        overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    cat_support = discord.utils.get(guild.categories, name="┣━━ 🎫 SUPORTE ━━┫")
    ticket_name = f"ticket-{tipo}-{user.name[:10]}".lower().replace(" ", "-")

    try:
        ticket_ch = await guild.create_text_channel(ticket_name, category=cat_support, overwrites=overwrites)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao criar ticket: {e}", ephemeral=True)
        return

    gd["tickets"][ticket_ch.id] = {
        "opener_id": user.id,
        "tipo": tipo,
        "assumed": False,
        "opened_at": datetime.datetime.utcnow(),
        "warned_12h": False,
        "auto_closing": False
    }

    await interaction.response.send_message(f"✅ Ticket criado! {ticket_ch.mention}", ephemeral=True)

    embed = discord.Embed(
        title=f"🎫 Ticket — {tipo.capitalize()}",
        description=(
            f"Olá {user.mention}! Seu ticket foi aberto.\n\n"
            f"**Tipo:** {tipo}\n"
            f"**Aberto em:** <t:{int(datetime.datetime.utcnow().timestamp())}:F>\n\n"
            "A equipe será notificada em breve."
        ),
        color=0x43b581,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text="Atendimento 24/7")

    member_view = MemberTicketView(user.id)
    await ticket_ch.send(content=f"{user.mention}", embed=embed, view=member_view)

    admin_view = AdminTicketView(user.id)
    embed_admin = discord.Embed(
        title="🛡️ Painel Admin/Support",
        description="Painel exclusivo para a equipe de suporte.",
        color=0x5865F2
    )
    await ticket_ch.send(embed=embed_admin, view=admin_view)

    notif_embed = discord.Embed(
        title="🔔 Novo Ticket Aberto!",
        description=f"**Usuário:** {user.mention} (`{user}`)\n**Tipo:** {tipo}\n**Canal:** {ticket_ch.mention}",
        color=0xffa500,
        timestamp=datetime.datetime.utcnow()
    )
    if guild.owner:
        try:
            await guild.owner.send(embed=notif_embed)
        except Exception:
            pass
    if support_role:
        for m in support_role.members:
            if m != guild.owner:
                try:
                    await m.send(embed=notif_embed)
                except Exception:
                    pass


class MemberTicketView(discord.ui.View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    async def check_perm(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opener_id:
            await interaction.response.send_message("❌ Apenas quem abriu o ticket pode usar este painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Chamar Admin/Support", emoji="📣", style=discord.ButtonStyle.blurple, custom_id="member_call_admin")
    async def call_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_perm(interaction):
            return
        guild = interaction.guild
        gd = get_gd(guild.id)
        support_role = guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
        embed = discord.Embed(
            title="📣 Membro Chamando Suporte!",
            description=f"{interaction.user.mention} aguarda atendimento neste ticket.",
            color=0xffa500
        )
        await interaction.channel.send(embed=embed)
        notif = discord.Embed(title="🔔 Membro Chamando!", description=f"{interaction.user.mention} chamou suporte no ticket {interaction.channel.mention}", color=0xffa500)
        if guild.owner:
            try: await guild.owner.send(embed=notif)
            except: pass
        if support_role:
            for m in support_role.members:
                try: await m.send(embed=notif)
                except: pass
        await interaction.response.send_message("✅ Suporte notificado!", ephemeral=True)

    @discord.ui.button(label="Cancelar Ticket", emoji="❌", style=discord.ButtonStyle.red, custom_id="member_cancel_ticket")
    async def cancel_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_perm(interaction):
            return
        gd = get_gd(interaction.guild.id)
        tinfo = gd["tickets"].get(interaction.channel.id, {})
        await interaction.response.send_message("⚠️ Ticket será cancelado em **6 segundos**...", ephemeral=False)
        await asyncio.sleep(6)
        await _close_ticket_channel(interaction.guild, interaction.channel, tinfo, f"Cancelado pelo membro {interaction.user}")
        gd["tickets"].pop(interaction.channel.id, None)


class AdminTicketView(discord.ui.View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    async def check_admin(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        gd = get_gd(guild.id)
        support_role = guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
        is_owner = interaction.user.id == guild.owner_id
        is_support = support_role in interaction.user.roles if support_role else False
        has_owner_role = discord.utils.get(interaction.user.roles, name="👑 Owner") is not None
        has_admin_role = discord.utils.get(interaction.user.roles, name="🛡️ Admin") is not None
        if not (is_owner or is_support or has_owner_role or has_admin_role):
            await interaction.response.send_message("❌ Apenas admins/support podem usar este painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Assumir Ticket", emoji="✅", style=discord.ButtonStyle.green, custom_id="admin_assume")
    async def assume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_admin(interaction):
            return
        gd = get_gd(interaction.guild.id)
        tinfo = gd["tickets"].get(interaction.channel.id)
        if not tinfo:
            await interaction.response.send_message("❌ Ticket não encontrado.", ephemeral=True)
            return
        tinfo["assumed"] = True
        tinfo["assumed_by"] = interaction.user.id
        embed = discord.Embed(title="✅ Ticket Assumido", description=f"{interaction.user.mention} assumiu este ticket!", color=0x43b581)
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Você assumiu o ticket!", ephemeral=True)

    @discord.ui.button(label="Chamar Membro", emoji="📢", style=discord.ButtonStyle.blurple, custom_id="admin_call_member")
    async def call_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_admin(interaction):
            return
        opener = interaction.guild.get_member(self.opener_id)
        embed = discord.Embed(title="📢 Admin Chamando!", description=f"{opener.mention if opener else 'Membro'}, o admin **{interaction.user.display_name}** está chamando você!", color=0x5865F2)
        await interaction.channel.send(content=f"{opener.mention if opener else ''}", embed=embed)
        if opener:
            try:
                await opener.send(embed=discord.Embed(title="📢 Você foi chamado!", description=f"O admin **{interaction.user.display_name}** está chamando você no ticket {interaction.channel.mention}", color=0x5865F2))
            except: pass
        await interaction.response.send_message("✅ Membro notificado!", ephemeral=True)

    @discord.ui.button(label="Fechar Ticket", emoji="🔒", style=discord.ButtonStyle.red, custom_id="admin_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_admin(interaction):
            return
        gd = get_gd(interaction.guild.id)
        tinfo = gd["tickets"].get(interaction.channel.id, {})
        await interaction.response.send_message("🔒 Ticket fechando em **6 segundos**...", ephemeral=False)
        await asyncio.sleep(6)
        await _close_ticket_channel(interaction.guild, interaction.channel, tinfo, f"Fechado pelo admin {interaction.user}")
        gd["tickets"].pop(interaction.channel.id, None)


# ============================================================
# COMANDOS DE GERENCIAMENTO
# ============================================================
@tree.command(name="suport_cargo", description="Define o cargo de suporte (apenas dono)")
@app_commands.describe(cargo="Cargo que receberá permissões de suporte")
async def suport_cargo(interaction: discord.Interaction, cargo: discord.Role):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono** pode usar este comando!", ephemeral=True)
        return
    gd = get_gd(interaction.guild.id)
    gd["support_role_id"] = cargo.id
    await cargo.edit(permissions=discord.Permissions(
        read_messages=True, send_messages=True, manage_channels=True,
        read_message_history=True, attach_files=True, embed_links=True,
        manage_messages=True, use_application_commands=True
    ))
    embed = discord.Embed(title="✅ Cargo de Suporte Definido", description=f"O cargo {cargo.mention} agora é a equipe de suporte!", color=0x43b581)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="add_usuario", description="Adiciona um usuário à equipe de suporte (apenas dono)")
@app_commands.describe(usuario="Usuário a adicionar")
async def add_usuario(interaction: discord.Interaction, usuario: discord.Member):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono** pode usar este comando!", ephemeral=True)
        return
    gd = get_gd(interaction.guild.id)
    support_role = interaction.guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
    if not support_role:
        await interaction.response.send_message("❌ Defina primeiro o cargo de suporte com `/suport_cargo`!", ephemeral=True)
        return
    await usuario.add_roles(support_role)
    if usuario.id not in gd["support_users"]:
        gd["support_users"].append(usuario.id)
    embed = discord.Embed(title="✅ Usuário Adicionado ao Suporte", description=f"{usuario.mention} agora faz parte da equipe de suporte!", color=0x43b581)
    await interaction.response.send_message(embed=embed)
    try:
        await usuario.send(embed=discord.Embed(title="🎉 Bem-vindo ao Suporte!", description=f"Você foi adicionado à equipe de suporte de **{interaction.guild.name}**!", color=0x43b581))
    except: pass


@tree.command(name="delet_user", description="Remove um usuário da equipe de suporte (apenas dono)")
@app_commands.describe(usuario="Usuário a remover")
async def delet_user(interaction: discord.Interaction, usuario: discord.Member):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono** pode usar este comando!", ephemeral=True)
        return
    gd = get_gd(interaction.guild.id)
    support_role = interaction.guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
    if support_role and support_role in usuario.roles:
        await usuario.remove_roles(support_role)
    if usuario.id in gd["support_users"]:
        gd["support_users"].remove(usuario.id)
    embed = discord.Embed(title="✅ Usuário Removido do Suporte", description=f"{usuario.mention} foi removido da equipe de suporte.", color=0xf04747)
    await interaction.response.send_message(embed=embed)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Painel Web Bot 1 rodando em http://0.0.0.0:8080")

    # Registrar views persistentes
    bot.add_view(TicketPanelView())

    bot.run(TOKEN)
