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
# CONFIGURAÇÕES — 2 TOKENS (variáveis de ambiente)
# ============================================================
TOKEN_1 = os.environ.get("DISCORD_TOKEN_1", "")   # Bot principal (este código)

BOT_START_TIME = time.time()
bot_running = True

# IDs de canais que NUNCA serão deletados pelo /create
PROTECTED_CHANNEL_IDS = {
    1472068898567491597,
    1473485452768972933,
}

# ============================================================
# FLASK — PAINEL WEB
# ============================================================
app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Bot Dashboard</title>
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
    .btn-green:hover { background:#3ca374; }
    .btn-red { background:#f04747; color:#fff; }
    .btn-red:hover { background:#d93636; }
    .btn-blue { background:#5865F2; color:#fff; }
    .btn-blue:hover { background:#4752c4; }
    .actions { display:flex; gap:14px; flex-wrap:wrap; }
    .log-box { background:#0d0d0d; border-radius:8px; padding:14px 18px; font-family:monospace; font-size:.82rem; color:#43b581; max-height:200px; overflow-y:auto; border:1px solid #2a2a4a; }
    .status-dot { width:10px; height:10px; border-radius:50%; background:#43b581; display:inline-block; margin-right:6px; animation:pulse 1.5s infinite; }
    .status-dot.off { background:#f04747; animation:none; }
    @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
    footer { margin-top:auto; padding:18px; color:#555; font-size:.8rem; }
  </style>
</head>
<body>
  <header>
    <div class="status-dot" id="sdot"></div>
    <h1>🤖 Discord Bot — Dashboard</h1>
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
        <button class="btn btn-red" onclick="controlBot('stop')">⏹ Desligar Bot</button>
        <button class="btn btn-green" onclick="controlBot('restart')">🔁 Reiniciar Bot</button>
      </div>
    </div>
    <div class="card">
      <h2>📜 Log de Atividade</h2>
      <div class="log-box" id="logBox">Aguardando logs...</div>
    </div>
  </div>
  <footer>Bot Dashboard &copy; 2025 — Powered by discord.py</footer>
  <script>
    const logs = [];
    function addLog(msg) {
      const t = new Date().toLocaleTimeString('pt-BR');
      logs.unshift(`[${t}] ${msg}`);
      if(logs.length>40) logs.pop();
      document.getElementById('logBox').innerText = logs.join('\\n');
    }
    async function fetchStats() {
      try {
        const r = await fetch('/api/stats');
        const d = await r.json();
        document.getElementById('uptime').innerText = d.uptime;
        document.getElementById('guilds').innerText = d.guilds;
        document.getElementById('users').innerText = d.users;
        document.getElementById('latency').innerText = d.latency;
        const online = d.status === 'online';
        document.getElementById('statusBadge').innerText = online ? 'ONLINE' : 'OFFLINE';
        document.getElementById('statusBadge').className = 'badge' + (online?'':' offline');
        document.getElementById('sdot').className = 'status-dot' + (online?'':' off');
        addLog(`Stats atualizadas — ${d.guilds} servidor(es), latência ${d.latency}ms`);
      } catch(e) { addLog('Erro ao buscar stats'); }
    }
    async function controlBot(action) {
      if(action==='stop' && !confirm('Deseja desligar o bot?')) return;
      if(action==='restart' && !confirm('Deseja reiniciar o bot?')) return;
      try {
        const r = await fetch('/api/control', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action})});
        const d = await r.json();
        addLog(`Ação: ${action} — ${d.message}`);
        setTimeout(fetchStats, 3000);
      } catch(e) { addLog('Erro ao enviar comando'); }
    }
    fetchStats();
    setInterval(fetchStats, 30000);
    addLog('Dashboard carregado com sucesso!');
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

@app.route("/api/control", methods=["POST"])
def api_control():
    global bot_running
    data = request.get_json() or {}
    action = data.get("action", "")
    if action == "stop":
        bot_running = False
        asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)
        return jsonify({"message": "Bot desligado."})
    elif action == "restart":
        bot_running = True
        return jsonify({"message": "Reinicialização solicitada. Reinicie o processo manualmente no Replit."})
    return jsonify({"message": "Ação desconhecida."}), 400

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ============================================================
# BOT SECUNDÁRIO (simples, só fica online)
# ============================================================
class Bot2(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())

    async def on_ready(self):
        print(f"✅ [Bot2] Online como {self.user}")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="o servidor 👀"
        ))

bot2 = Bot2()

async def run_bot2():
    if TOKEN_2:
        try:
            await bot2.start(TOKEN_2)
        except Exception as e:
            print(f"❌ [Bot2] Erro: {e}")
    else:
        print("⚠️ [Bot2] TOKEN_2 não definido, bot secundário não iniciado.")

# ============================================================
# BOT PRINCIPAL
# ============================================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Storage em memória
guild_data = {}

def get_gd(guild_id):
    if guild_id not in guild_data:
        guild_data[guild_id] = {
            "support_role_id": None,
            "support_users": [],
            "tickets": {},
            "member_count_msg_id": None,
            "member_count_ch_id": None,
            "invite_msg_id": None,
            "invite_ch_id": None,
        }
    return guild_data[guild_id]

# ============================================================
# EVENTOS
# ============================================================
@bot.event
async def on_ready():
    print(f"✅ [Bot1] Online como {bot.user}")
    await tree.sync()
    auto_close_tickets.start()
    update_member_count.start()
    print("✅ Tasks iniciadas.")

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    gd = get_gd(guild.id)

    # ── Auto Role: cargo Membro instantâneo ──
    member_role = discord.utils.get(guild.roles, name="🟢 Membro")
    if not member_role:
        member_role = discord.utils.get(guild.roles, name="Membro")
    if member_role:
        try:
            await member.add_roles(member_role, reason="Auto-Role automático")
        except Exception as e:
            print(f"Auto-role erro: {e}")

    # ── Boas-vindas ──
    welcome_ch = discord.utils.get(guild.text_channels, name="「👋」boas-vindas")
    if welcome_ch:
        embed = discord.Embed(
            title=f"✨ Bem-vindo(a) ao {guild.name}!",
            description=(
                f"Olá {member.mention}, seja muito bem-vindo(a)! 🎉\n\n"
                f"📌 Leia as **regras** antes de interagir.\n"
                f"🎫 Em caso de dúvidas, abra um **ticket**.\n"
                f"🟢 Você já recebeu o cargo de **Membro** automaticamente!"
            ),
            color=0x5865F2,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if guild.icon:
            embed.set_image(url=guild.icon.url)
        embed.set_footer(text=f"Membro #{guild.member_count} • {guild.name}")
        await welcome_ch.send(content=member.mention, embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild

    # ── Despedida ──
    farewell_ch = discord.utils.get(guild.text_channels, name="「👋」boas-vindas")
    if farewell_ch:
        embed = discord.Embed(
            title=f"😢 {member.display_name} saiu do servidor",
            description=(
                f"**{member.mention}** deixou o **{guild.name}**.\n\n"
                f"Esperamos que volte um dia! 🙁\n"
                f"Agora somos **{guild.member_count}** membros."
            ),
            color=0xf04747,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{guild.name} • Até mais!")
        await farewell_ch.send(embed=embed)

    # ── Log de saída ──
    logs_ch = discord.utils.get(guild.text_channels, name="「🔍」logs-gerais")
    if logs_ch:
        embed_log = discord.Embed(
            title="🚪 Membro Saiu",
            description=f"**{member}** (`{member.id}`) saiu do servidor.",
            color=0xf04747,
            timestamp=datetime.datetime.utcnow()
        )
        embed_log.set_thumbnail(url=member.display_avatar.url)
        await logs_ch.send(embed=embed_log)

# ============================================================
# TASK: atualizar contagem de membros a cada 1 hora
# ============================================================
@tasks.loop(hours=1)
async def update_member_count():
    for guild_id, gd in guild_data.items():
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
        ch_id = gd.get("member_count_ch_id")
        msg_id = gd.get("member_count_msg_id")
        if not ch_id or not msg_id:
            continue
        ch = guild.get_channel(ch_id)
        if not ch:
            continue
        try:
            msg = await ch.fetch_message(msg_id)
            embed = discord.Embed(
                title=f"👥 {guild.member_count} Membros",
                description="Contagem atualizada automaticamente a cada hora!",
                color=0x43b581,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_footer(text="Última atualização")
            await msg.edit(embed=embed)
        except Exception as e:
            print(f"update_member_count erro: {e}")

# ============================================================
# TASK: fechar tickets automaticamente
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
                        description=f"O ticket {ch.mention} está aberto há mais de 12 horas sem atendimento.",
                        color=0xffa500, timestamp=now
                    )
                    await log_ch.send(embed=embed)
            if assumed and delta > 68400 and not tinfo.get("auto_closing"):
                tinfo["auto_closing"] = True
                await ch.send("⏰ Este ticket será fechado automaticamente em 6 segundos por inatividade (19h).")
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
        color=0xf04747, timestamp=datetime.datetime.utcnow()
    )
    if log_ch:
        await log_ch.send(embed=embed)
    if opener:
        try: await opener.send(embed=embed)
        except: pass
    if guild.owner:
        try: await guild.owner.send(embed=embed)
        except: pass
    try: await channel.delete(reason=motivo)
    except: pass
    cat = channel.category
    if cat and len(cat.channels) == 0:
        try: await cat.delete()
        except: pass

# ============================================================
# HELPER: CRIAR TODA A ESTRUTURA DO SERVIDOR
# ============================================================
async def _build_server(guild: discord.Guild, protected_role_ids: set = None, protected_channel_ids: set = None):
    """
    Apaga todos os cargos (exceto protegidos) e canais (exceto protegidos), depois recria tudo.
    """
    if protected_role_ids is None:
        protected_role_ids = set()
    if protected_channel_ids is None:
        protected_channel_ids = set()

    all_protected_ch = PROTECTED_CHANNEL_IDS | protected_channel_ids

    # ── 1. APAGAR CANAIS ──
    for ch in list(guild.channels):
        if ch.id in all_protected_ch:
            continue
        try:
            await ch.delete(reason="/create — recriando servidor")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"Erro ao apagar canal {ch.name}: {e}")

    # ── 2. APAGAR CARGOS ──
    for role in list(guild.roles):
        if role.is_default():
            continue
        if role.id in protected_role_ids:
            continue
        if role.managed:
            continue
        try:
            await role.delete(reason="/create — recriando cargos")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"Erro ao apagar cargo {role.name}: {e}")

    # ── 3. CRIAR CARGOS ──

    await guild.default_role.edit(permissions=discord.Permissions(
        read_messages=False, send_messages=False
    ))

    owner_role = await guild.create_role(
        name="👑 Owner", color=discord.Color.gold(),
        permissions=discord.Permissions(administrator=True),
        hoist=True, reason="Setup"
    )

    co_owner_role = await guild.create_role(
        name="🔱 Co-Owner", color=discord.Color.from_str("#e74c3c"),
        permissions=discord.Permissions(administrator=True),
        hoist=True, reason="Setup"
    )

    gerente_role = await guild.create_role(
        name="💼 Gerente", color=discord.Color.from_str("#e67e22"),
        permissions=discord.Permissions(
            manage_guild=True, manage_channels=True, manage_roles=True,
            kick_members=True, ban_members=True, read_messages=True,
            send_messages=True, manage_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True,
            mention_everyone=True, view_audit_log=True
        ),
        hoist=True, reason="Setup"
    )

    support_role = await guild.create_role(
        name="🛡️ Support", color=discord.Color.green(),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, manage_channels=True,
            read_message_history=True, attach_files=True, embed_links=True,
            manage_messages=True, use_application_commands=True, kick_members=True
        ),
        hoist=True, reason="Setup"
    )

    mod_role = await guild.create_role(
        name="⚔️ Moderador", color=discord.Color.from_str("#3498db"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, manage_messages=True,
            kick_members=True, read_message_history=True, embed_links=True,
            attach_files=True, use_application_commands=True
        ),
        hoist=True, reason="Setup"
    )

    divulgador_role = await guild.create_role(
        name="📢 Divulgador", color=discord.Color.from_str("#9b59b6"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True
        ),
        hoist=True, reason="Setup"
    )

    parceiro_role = await guild.create_role(
        name="🤝 Parceiro", color=discord.Color.from_str("#1abc9c"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True
        ),
        hoist=True, reason="Setup"
    )

    vendedor_role = await guild.create_role(
        name="💰 Vendedor", color=discord.Color.from_str("#f39c12"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True
        ),
        hoist=True, reason="Setup"
    )

    comprador_role = await guild.create_role(
        name="🛒 Comprador", color=discord.Color.from_str("#27ae60"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True
        ),
        hoist=True, reason="Setup"
    )

    user_logs_role = await guild.create_role(
        name="📋 User Logs", color=discord.Color.from_str("#95a5a6"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=False, read_message_history=True
        ),
        reason="Setup"
    )

    vip_role = await guild.create_role(
        name="⭐ VIP", color=discord.Color.from_str("#f1c40f"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, embed_links=True,
            attach_files=True, read_message_history=True, use_application_commands=True
        ),
        hoist=True, reason="Setup"
    )

    member_role = await guild.create_role(
        name="🟢 Membro", color=discord.Color.from_str("#7289da"),
        permissions=discord.Permissions(
            read_messages=True, send_messages=True, read_message_history=True,
            attach_files=True, embed_links=True, add_reactions=True,
            use_application_commands=True, connect=True, speak=True
        ),
        reason="Setup — Auto-Role"
    )

    # Dar cargos ao dono
    try:
        owner_member = guild.get_member(guild.owner_id)
        if owner_member:
            await owner_member.add_roles(owner_role, support_role, gerente_role, reason="Setup")
    except Exception as e:
        print(f"Erro ao dar cargos ao dono: {e}")

    gd = get_gd(guild.id)
    gd["support_role_id"] = support_role.id

    # ── FUNÇÕES DE OVERWRITES ──
    def ow_info():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            comprador_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            vendedor_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            divulgador_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            parceiro_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            vip_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            gerente_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            co_owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

    def ow_chat():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True, add_reactions=True),
            comprador_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            vendedor_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            divulgador_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            parceiro_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            vip_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, use_external_emojis=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            gerente_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            co_owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

    def ow_media():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            divulgador_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            vendedor_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            parceiro_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            vip_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

    def ow_logs():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=False),
            user_logs_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            gerente_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            co_owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

    def ow_admin():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=False),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            gerente_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            co_owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

    def ow_divulg():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            divulgador_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            parceiro_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

    def ow_compra():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            comprador_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            vendedor_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            vip_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

    def ow_ticket():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            gerente_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

    voice_ow = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=False),
        member_role: discord.PermissionOverwrite(connect=True, speak=True, view_channel=True),
        vip_role: discord.PermissionOverwrite(connect=True, speak=True, view_channel=True, priority_speaker=True),
        support_role: discord.PermissionOverwrite(connect=True, speak=True, mute_members=True, deafen_members=True, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, speak=True, mute_members=True, deafen_members=True, view_channel=True, manage_channels=True),
    }

    # ── 4. CRIAR CATEGORIAS E CANAIS ──

    cat_info = await guild.create_category("┏━━ 📌 INFORMAÇÕES ━━┓", position=0)
    ch_invites   = await guild.create_text_channel("「🔗」convite",      category=cat_info, overwrites=ow_info())
    ch_members   = await guild.create_text_channel("「👥」membros",      category=cat_info, overwrites=ow_info())
    ch_rules     = await guild.create_text_channel("「📜」regras",       category=cat_info, overwrites=ow_info())
    ch_avisos    = await guild.create_text_channel("「📣」avisos",        category=cat_info, overwrites=ow_info())
    ch_welcome   = await guild.create_text_channel("「👋」boas-vindas",  category=cat_info, overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    })

    cat_parceria = await guild.create_category("┣━━ 🤝 PARCERIA ━━┫")
    ch_parceria_info = await guild.create_text_channel("「🤝」como-ser-parceiro",       category=cat_parceria, overwrites=ow_info())
    await guild.create_text_channel("「📢」divulgações-parceiros", category=cat_parceria, overwrites=ow_divulg())

    cat_chat = await guild.create_category("┣━━ 💬 CHAT ━━┫")
    await guild.create_text_channel("「💬」geral",     category=cat_chat, overwrites=ow_chat())
    await guild.create_text_channel("「😂」memes",     category=cat_chat, overwrites=ow_chat())
    await guild.create_text_channel("「🎮」jogos",     category=cat_chat, overwrites=ow_chat())
    await guild.create_text_channel("「🤳」off-topic", category=cat_chat, overwrites=ow_chat())

    cat_media = await guild.create_category("┣━━ 📸 MÍDIA ━━┫")
    await guild.create_text_channel("「📸」fotos",   category=cat_media, overwrites=ow_media())
    await guild.create_text_channel("「🎬」vídeos",  category=cat_media, overwrites=ow_media())
    await guild.create_text_channel("「🎵」músicas", category=cat_media, overwrites=ow_media())

    cat_divulg = await guild.create_category("┣━━ 📢 DIVULGAÇÃO ━━┫")
    await guild.create_text_channel("「📢」divulgue-aqui", category=cat_divulg, overwrites=ow_divulg())
    await guild.create_text_channel("「🔥」promoções",     category=cat_divulg, overwrites=ow_divulg())

    cat_compras = await guild.create_category("┣━━ 🛒 COMPRAS & VENDAS ━━┫")
    await guild.create_text_channel("「💰」produtos",           category=cat_compras, overwrites=ow_compra())
    await guild.create_text_channel("「🛒」compras-e-vendas",   category=cat_compras, overwrites=ow_compra())
    await guild.create_text_channel("「✅」compras-verificadas", category=cat_compras, overwrites=ow_info())

    cat_cmds = await guild.create_category("┣━━ ⚡ COMANDOS ━━┫")
    cmd_ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, use_application_commands=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    await guild.create_text_channel("「⚡」bot-cmds",  category=cat_cmds, overwrites=cmd_ow)
    ch_hits      = await guild.create_text_channel("「🏆」hits",         category=cat_cmds, overwrites=ow_info())
    ch_tutorial  = await guild.create_text_channel("「📖」tutorial-key", category=cat_cmds, overwrites=ow_info())
    ch_logs_user = await guild.create_text_channel("「📝」criar-log",    category=cat_cmds, overwrites=ow_chat())

    cat_support_cat = await guild.create_category("┣━━ 🎫 SUPORTE ━━┫")
    ch_tickets   = await guild.create_text_channel("「🎫」tickets",      category=cat_support_cat, overwrites=ow_ticket())

    cat_staff = await guild.create_category("┣━━ 🛡️ STAFF ━━┫")
    await guild.create_text_channel("「💬」chat-staff",     category=cat_staff, overwrites=ow_admin())
    await guild.create_text_channel("「📋」relatórios",     category=cat_staff, overwrites=ow_admin())
    await guild.create_text_channel("「⚙️」comandos-staff", category=cat_staff, overwrites=ow_admin())

    cat_logs = await guild.create_category("┗━━ 📋 LOGS ━━┛")
    await guild.create_text_channel("「📋」logs-tickets", category=cat_logs, overwrites=ow_logs())
    await guild.create_text_channel("「🔍」logs-gerais",  category=cat_logs, overwrites=ow_logs())
    await guild.create_text_channel("「👤」logs-membros", category=cat_logs, overwrites=ow_logs())
    await guild.create_text_channel("「💸」logs-vendas",  category=cat_logs, overwrites=ow_logs())

    cat_voice = await guild.create_category("┣━━ 🔊 VOZ ━━┫")
    await guild.create_voice_channel("「🔊」Geral",  category=cat_voice, overwrites=voice_ow)
    await guild.create_voice_channel("「🎮」Games",  category=cat_voice, overwrites=voice_ow)
    await guild.create_voice_channel("「🎵」Música", category=cat_voice, overwrites=voice_ow)
    await guild.create_voice_channel("「🛡️」Staff", category=cat_voice, overwrites={
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=False),
        support_role: discord.PermissionOverwrite(connect=True, speak=True, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, speak=True, view_channel=True),
    })

    # ── 5. PREENCHER CANAIS ──

    invite = await ch_invites.create_invite(max_age=0, max_uses=0)
    embed_inv = discord.Embed(
        title="🔗 Convide seus amigos!",
        description=f"**Link permanente do servidor:**\n```{invite.url}```\nCompartilhe e ajude nossa comunidade a crescer! 💜",
        color=0x5865F2
    )
    embed_inv.set_footer(text=guild.name)
    msg_inv = await ch_invites.send(embed=embed_inv)
    gd["invite_msg_id"] = msg_inv.id
    gd["invite_ch_id"] = ch_invites.id

    embed_mem = discord.Embed(
        title=f"👥 {guild.member_count} Membros",
        description="A contagem é atualizada automaticamente toda hora!",
        color=0x43b581,
        timestamp=datetime.datetime.utcnow()
    )
    embed_mem.set_footer(text="Atualizado automaticamente")
    msg_mem = await ch_members.send(embed=embed_mem)
    gd["member_count_msg_id"] = msg_mem.id
    gd["member_count_ch_id"] = ch_members.id

    embed_rules = discord.Embed(
        title="📜 Regras do Servidor",
        description=(
            "**Bem-vindo às regras! Leia com atenção.**\n\n"
            "**1️⃣ Respeito acima de tudo**\n"
            "Trate todos com respeito. Não toleramos xingamentos, ofensas ou discriminação.\n\n"
            "**2️⃣ Sem spam ou flood**\n"
            "Não mande mensagens repetidas ou fique fazendo spam nos canais.\n\n"
            "**3️⃣ Sem conteúdo ilegal ou +18**\n"
            "Qualquer conteúdo impróprio será deletado e o usuário punido.\n\n"
            "**4️⃣ Sem divulgações sem permissão**\n"
            "Use apenas os canais corretos para divulgar. Divulgação sem permissão = ban.\n\n"
            "**5️⃣ Sem tópicos polêmicos**\n"
            "Evite discussões sobre política, religião ou temas divisivos.\n\n"
            "**6️⃣ Siga as diretrizes do Discord**\n"
            "Respeite os [Termos de Serviço](https://discord.com/terms) do Discord.\n\n"
            "**7️⃣ Obedeça admins e moderadores**\n"
            "Decisões da equipe são finais. Dúvidas? Abra um ticket.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ Ao participar, você concorda com todas as regras acima."
        ),
        color=0xf04747
    )
    embed_rules.set_footer(text=f"{guild.name} — Leia com atenção")
    await ch_rules.send(embed=embed_rules)

    embed_avisos = discord.Embed(
        title="📣 Canal de Avisos",
        description="Este canal é exclusivo para avisos importantes da equipe.\nAcompanhe para não perder novidades! 👀",
        color=0xffa500
    )
    await ch_avisos.send(embed=embed_avisos)

    embed_parceria = discord.Embed(
        title="🤝 Como se tornar Parceiro?",
        description=(
            "Quer fazer uma parceria conosco? Siga os passos:\n\n"
            "**1️⃣** Abra um ticket em `「🎫」tickets`\n"
            "**2️⃣** Selecione a opção **Parceria**\n"
            "**3️⃣** Apresente seu servidor/projeto\n"
            "**4️⃣** Aguarde a análise da equipe\n\n"
            "✅ Parceiros recebem o cargo 🤝 Parceiro e acesso ao canal de divulgação!"
        ),
        color=0x1abc9c
    )
    await ch_parceria_info.send(embed=embed_parceria)

    embed_tut = discord.Embed(
        title="📖 Tutorial — Como Gerar sua Key",
        description=(
            "**Passo 1:** Vá até o canal `「⚡」bot-cmds`\n"
            "**Passo 2:** Use o comando `/gerar_key`\n"
            "**Passo 3:** Copie a key gerada e guarde em lugar seguro\n"
            "**Passo 4:** Use a key para acessar recursos exclusivos\n\n"
            "⚠️ Cada usuário pode gerar apenas **1 key** por conta.\n"
            "📩 Dúvidas? Abra um ticket em `「🎫」tickets`"
        ),
        color=0x7289da
    )
    embed_tut.set_footer(text=f"{guild.name} — Sistema de Keys")
    await ch_tutorial.send(embed=embed_tut)

    embed_hits = discord.Embed(
        title="🏆 Hall of Fame — Hits",
        description="Aqui ficam registrados os maiores hits e conquistas dos nossos membros!\nUse `/hit` para registrar o seu! 🎯",
        color=0xffd700
    )
    await ch_hits.send(embed=embed_hits)

    embed_log_user = discord.Embed(
        title="📝 Crie sua Log",
        description="Registre suas atividades e conquistas aqui!\nDigite livremente para criar sua log pessoal. 🗒️",
        color=0x99aab5
    )
    await ch_logs_user.send(embed=embed_log_user)

    # ── 6. PAINEL DE TICKETS ──
    embed_ticket = discord.Embed(
        title="🎫 Central de Suporte",
        description=(
            "Bem-vindo à Central de Suporte!\n\n"
            "Clique em um dos botões abaixo para abrir um atendimento:\n\n"
            "🟢 **Abrir Ticket** — Fale com a equipe\n"
            "🤝 **Parceria** — Proposta de parceria\n"
            "❓ **Dúvidas** — Tire suas dúvidas\n"
            "💳 **Pagamento** — Formas de pagamento\n"
            "📝 **Criar Log** — Crie sua log pessoal\n\n"
            "⏰ Atendimento **24/7** • Resposta em até 12h"
        ),
        color=0x5865F2
    )
    embed_ticket.set_footer(text=f"{guild.name} — Suporte 24/7")
    if guild.icon:
        embed_ticket.set_thumbnail(url=guild.icon.url)

    view_ticket = TicketPanelView()
    await ch_tickets.send(embed=embed_ticket, view=view_ticket)

    return support_role, member_role

# ============================================================
# COMANDO /create
# ============================================================
@tree.command(name="create", description="Apaga e recria todos os canais e cargos do servidor (apenas dono)")
async def create_command(interaction: discord.Interaction):
    guild = interaction.guild
    if interaction.user.id != guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono do servidor** pode usar este comando!", ephemeral=True)
        return

    await interaction.response.send_message(
        "⚙️ Iniciando configuração completa...\n"
        "⚠️ Todos os canais e cargos serão apagados e recriados!\n"
        f"🔒 Canais protegidos (IDs fixos) **não serão apagados**.",
        ephemeral=True
    )

    try:
        await _build_server(guild)
        ch = discord.utils.get(guild.text_channels, name="「💬」geral")
        if ch:
            await ch.send("✅ **Servidor configurado com sucesso!** Use `/suport_cargo` para definir o cargo de suporte. 🎉")
    except Exception as e:
        try:
            await interaction.followup.send(f"❌ Erro durante o setup: `{e}`", ephemeral=True)
        except:
            pass
        print(f"Erro /create: {e}")

# ============================================================
# MODAL /create2
# ============================================================
class Create2Modal(discord.ui.Modal, title="🛡️ Preservar Canais e Cargos"):
    canais_input = discord.ui.TextInput(
        label="IDs de canais para PRESERVAR (separados por vírgula)",
        placeholder="Ex: 123456789, 987654321",
        required=False,
        style=discord.TextStyle.short
    )
    cargos_input = discord.ui.TextInput(
        label="IDs de cargos para PRESERVAR (separados por vírgula)",
        placeholder="Ex: 111222333, 444555666",
        required=False,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild

        protected_chs = set()
        raw_chs = self.canais_input.value.strip()
        if raw_chs:
            for part in raw_chs.split(","):
                try:
                    protected_chs.add(int(part.strip()))
                except ValueError:
                    pass

        protected_roles = set()
        raw_roles = self.cargos_input.value.strip()
        if raw_roles:
            for part in raw_roles.split(","):
                try:
                    protected_roles.add(int(part.strip()))
                except ValueError:
                    pass

        await interaction.response.send_message(
            f"⚙️ Iniciando setup personalizado...\n"
            f"🔒 Canais extras protegidos: `{protected_chs}`\n"
            f"🔒 Cargos protegidos: `{protected_roles}`",
            ephemeral=True
        )

        try:
            await _build_server(guild, protected_role_ids=protected_roles, protected_channel_ids=protected_chs)
            ch = discord.utils.get(guild.text_channels, name="「💬」geral")
            if ch:
                await ch.send("✅ **Servidor configurado com sucesso! (Setup personalizado)** 🎉")
        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Erro: `{e}`", ephemeral=True)
            except:
                pass
            print(f"Erro /create2: {e}")

@tree.command(name="create2", description="Recria o servidor preservando canais/cargos escolhidos (apenas dono)")
async def create2_command(interaction: discord.Interaction):
    guild = interaction.guild
    if interaction.user.id != guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono do servidor** pode usar este comando!", ephemeral=True)
        return
    await interaction.response.send_modal(Create2Modal())

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
            f"Olá {user.mention}! Seu ticket foi aberto com sucesso.\n\n"
            f"**Tipo:** {tipo}\n"
            f"**Aberto em:** <t:{int(datetime.datetime.utcnow().timestamp())}:F>\n\n"
            "A equipe de suporte será notificada em breve.\nUse o painel abaixo para interagir."
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
        try: await guild.owner.send(embed=notif_embed)
        except: pass
    if support_role:
        for m in support_role.members:
            if m != guild.owner:
                try: await m.send(embed=notif_embed)
                except: pass

# ── View do Membro no Ticket ──
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
            description=f"{interaction.user.mention} está aguardando atendimento neste ticket.",
            color=0xffa500
        )
        await interaction.channel.send(embed=embed)
        notif = discord.Embed(
            title="🔔 Membro Chamando!",
            description=f"{interaction.user.mention} chamou suporte no ticket {interaction.channel.mention}",
            color=0xffa500
        )
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

# ── View do Admin/Support no Ticket ──
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
        if not (is_owner or is_support or has_owner_role):
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
        embed = discord.Embed(
            title="✅ Ticket Assumido",
            description=f"{interaction.user.mention} assumiu este ticket e está atendendo.",
            color=0x43b581
        )
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Você assumiu o ticket!", ephemeral=True)

    @discord.ui.button(label="Chamar Membro", emoji="📢", style=discord.ButtonStyle.blurple, custom_id="admin_call_member")
    async def call_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_admin(interaction):
            return
        opener = interaction.guild.get_member(self.opener_id)
        embed = discord.Embed(
            title="📢 Admin/Support Chamando!",
            description=f"{opener.mention if opener else 'Membro'}, o admin **{interaction.user.display_name}** está chamando você!\nPor favor, responda o mais rápido possível.",
            color=0x5865F2
        )
        await interaction.channel.send(content=f"{opener.mention if opener else ''}", embed=embed)
        if opener:
            try:
                dm_embed = discord.Embed(
                    title="📢 Você foi chamado!",
                    description=f"O admin **{interaction.user.display_name}** está chamando você no ticket {interaction.channel.mention}",
                    color=0x5865F2
                )
                await opener.send(embed=dm_embed)
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
# COMANDOS SLASH DE GERENCIAMENTO
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
    embed = discord.Embed(
        title="✅ Cargo de Suporte Definido",
        description=f"O cargo {cargo.mention} agora é a equipe de suporte!",
        color=0x43b581
    )
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
    embed = discord.Embed(
        title="✅ Usuário Adicionado ao Suporte",
        description=f"{usuario.mention} agora faz parte da equipe de suporte!",
        color=0x43b581
    )
    await interaction.response.send_message(embed=embed)
    try:
        await usuario.send(embed=discord.Embed(
            title="🎉 Bem-vindo ao Suporte!",
            description=f"Você foi adicionado à equipe de suporte de **{interaction.guild.name}**!",
            color=0x43b581
        ))
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
    embed = discord.Embed(
        title="✅ Usuário Removido do Suporte",
        description=f"{usuario.mention} foi removido da equipe de suporte.",
        color=0xf04747
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="dar_cargo", description="Dá um cargo a um membro (apenas staff)")
@app_commands.describe(usuario="Membro alvo", cargo="Cargo a dar")
async def dar_cargo(interaction: discord.Interaction, usuario: discord.Member, cargo: discord.Role):
    guild = interaction.guild
    gd = get_gd(guild.id)
    is_owner = interaction.user.id == guild.owner_id
    support_role = guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
    is_staff = support_role in interaction.user.roles if support_role else False
    if not (is_owner or is_staff):
        await interaction.response.send_message("❌ Apenas staff pode usar este comando!", ephemeral=True)
        return
    await usuario.add_roles(cargo)
    await interaction.response.send_message(f"✅ Cargo {cargo.mention} dado para {usuario.mention}!", ephemeral=True)

@tree.command(name="remover_cargo", description="Remove um cargo de um membro (apenas staff)")
@app_commands.describe(usuario="Membro alvo", cargo="Cargo a remover")
async def remover_cargo(interaction: discord.Interaction, usuario: discord.Member, cargo: discord.Role):
    guild = interaction.guild
    gd = get_gd(guild.id)
    is_owner = interaction.user.id == guild.owner_id
    support_role = guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
    is_staff = support_role in interaction.user.roles if support_role else False
    if not (is_owner or is_staff):
        await interaction.response.send_message("❌ Apenas staff pode usar este comando!", ephemeral=True)
        return
    await usuario.remove_roles(cargo)
    await interaction.response.send_message(f"✅ Cargo {cargo.mention} removido de {usuario.mention}!", ephemeral=True)

# ============================================================
# MAIN — RODAR 2 BOTS SIMULTÂNEOS
# ============================================================
async def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Painel Web rodando em http://0.0.0.0:8080")

    bot.add_view(TicketPanelView())

    if TOKEN_1:
        await asyncio.gather(
            bot.start(TOKEN_1),
            run_bot2()
        )
    else:
        print("❌ TOKEN_1 não definido! Configure DISCORD_TOKEN_1 no ambiente.")

if __name__ == "__main__":
    asyncio.run(main())
