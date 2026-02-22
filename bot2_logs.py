import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import datetime
import aiohttp
from threading import Thread
from flask import Flask, jsonify, render_template_string
import time

# ============================================================
# CONFIGURAÇÕES
# ============================================================
TOKEN = os.environ.get("DISCORD_TOKEN_BOT2", "TOKEN_BOT2_AQUI")
BOT_START_TIME = time.time()

# Imagens
IMG_PAINEL = "https://i.imgur.com/sJUiZhI.jpeg"
IMG_VERIFICACAO = "https://i.imgur.com/VBADq0e.jpeg"

# ============================================================
# FLASK - PAINEL WEB (porta 8081 para não conflitar com Bot 1)
# ============================================================
app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>Bot 2 Online ✅</h1>", 200

@app.route("/ping")
def ping():
    return "OK", 200

@app.route("/api/stats")
def api_stats():
    uptime_sec = int(time.time() - BOT_START_TIME)
    h = uptime_sec // 3600
    m = (uptime_sec % 3600) // 60
    s = uptime_sec % 60
    try:
        guilds = len(bot2.guilds)
        latency = round(bot2.latency * 1000)
        status = "online"
    except Exception:
        guilds = 0; latency = 0; status = "offline"
    return jsonify({"status": status, "uptime": f"{h}h {m}m {s}s", "guilds": guilds, "latency": latency})

def run_flask():
    app.run(host="0.0.0.0", port=8081)

# ============================================================
# BOT 2
# ============================================================
intents = discord.Intents.all()
bot2 = commands.Bot(command_prefix="!!", intents=intents)
tree2 = bot2.tree

# Storage: {guild_id: {"logs_channel_id": int, "configured": bool, "verify_channel_id": int}}
guild_configs = {}
# Storage de canais privados abertos: {channel_id: {"opener_id": int, "guild_id": int, "opened_at": datetime, "assumed": bool, "closed": bool}}
private_channels = {}

def get_cfg(guild_id):
    if guild_id not in guild_configs:
        guild_configs[guild_id] = {
            "logs_channel_id": None,
            "configured": False,
            "verify_channel_id": None,
        }
    return guild_configs[guild_id]

# ============================================================
# EVENTOS
# ============================================================
@bot2.event
async def on_ready():
    print(f"✅ Bot 2 online como {bot2.user}")
    await tree2.sync()
    auto_close_private.start()
    print("✅ Bot 2 tasks iniciadas")

# ============================================================
# TASK: Auto fechar canais privados
# ============================================================
@tasks.loop(minutes=10)
async def auto_close_private():
    now = datetime.datetime.utcnow()
    to_close = []
    for ch_id, info in list(private_channels.items()):
        if info.get("closed"):
            to_close.append(ch_id)
            continue
        opened_at = info.get("opened_at")
        assumed = info.get("assumed", False)
        if not opened_at:
            continue
        delta = (now - opened_at).total_seconds()
        guild = bot2.get_guild(info["guild_id"])
        if not guild:
            to_close.append(ch_id)
            continue
        ch = guild.get_channel(ch_id)
        if not ch:
            to_close.append(ch_id)
            continue
        # Se não foi assumido: fecha após 9 horas (32400s)
        # Se foi assumido: não fecha automaticamente
        if not assumed and delta > 32400:
            try:
                await ch.send("⏰ Este canal será fechado em **6 segundos** por inatividade (9 horas).")
                await asyncio.sleep(6)
                await ch.delete(reason="Auto-close: 9 horas sem interação")
            except Exception:
                pass
            to_close.append(ch_id)
    for ch_id in to_close:
        private_channels.pop(ch_id, None)

# ============================================================
# COMANDO /reset — Deleta todos os dados do Bot 2 neste servidor
# ============================================================
@tree2.command(name="reset", description="Reseta todos os dados do Bot 2 neste servidor (apenas dono)")
async def reset_cmd(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono do servidor** pode usar este comando!", ephemeral=True)
        return
    guild_id = interaction.guild.id
    guild_configs.pop(guild_id, None)
    # Limpar canais privados deste servidor
    to_remove = [ch_id for ch_id, info in private_channels.items() if info.get("guild_id") == guild_id]
    for ch_id in to_remove:
        private_channels.pop(ch_id, None)
    embed = discord.Embed(
        title="🗑️ Dados Resetados",
        description="Todos os dados do Bot 2 neste servidor foram apagados!\nUse `/add_logs` para configurar novamente.",
        color=0xf04747
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================================
# COMANDO /add_logs — Inicia configuração, envia DM para dono
# ============================================================
@tree2.command(name="add_logs", description="Configura o sistema de logs de verificação (apenas dono)")
async def add_logs(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono do servidor** pode usar este comando!", ephemeral=True)
        return

    await interaction.response.send_message("📩 Enviando painel de configuração na sua DM...", ephemeral=True)

    # Enviar DM ao dono
    embed = discord.Embed(
        title="⚙️ Configuração do Sistema de Logs",
        description=(
            f"**Servidor:** {interaction.guild.name}\n\n"
            "Clique em **Configurar** abaixo para iniciar a configuração do sistema de logs de verificação.\n\n"
            "Você irá:\n"
            "• Selecionar o canal onde os membros poderão ver as logs\n"
            "• Criar o canal de verificação automaticamente\n"
        ),
        color=0x5865F2
    )
    embed.set_image(url=IMG_PAINEL)
    embed.set_footer(text=f"{interaction.guild.name} • Bot 2 Config")

    view = ConfigureDMView(interaction.guild.id, interaction.guild.name)
    try:
        await interaction.user.send(embed=embed, view=view)
    except discord.Forbidden:
        await interaction.followup.send("❌ Não consegui enviar DM! Verifique suas configurações de privacidade.", ephemeral=True)


class ConfigureDMView(discord.ui.View):
    def __init__(self, guild_id: int, guild_name: str):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.guild_name = guild_name

    @discord.ui.button(label="Configurar", emoji="⚙️", style=discord.ButtonStyle.blurple)
    async def configure(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar se é DM e o usuário é dono
        guild = bot2.get_guild(self.guild_id)
        if not guild or interaction.user.id != guild.owner_id:
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Selecione o Canal de Logs",
            description=(
                "Para configurar, vá ao **servidor** e use o comando:\n"
                "```/setup_logs_channel```\n"
                "Isso irá abrir um seletor de canal.\n\n"
                "**Ou** use o botão abaixo para configurar diretamente no servidor."
            ),
            color=0x43b581
        )
        await interaction.response.edit_message(embed=embed, view=ConfigureServerView(self.guild_id))


class ConfigureServerView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Criar Canal de Verificação", emoji="✅", style=discord.ButtonStyle.green)
    async def create_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = bot2.get_guild(self.guild_id)
        if not guild or interaction.user.id != guild.owner_id:
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return
        await interaction.response.send_message("⚙️ Criando canal de verificação...", ephemeral=True)
        # Criar no servidor
        await create_verification_channel(guild, interaction.user)


# ============================================================
# COMANDO /setup_logs_channel — Seleciona canal e cria verificação
# ============================================================
@tree2.command(name="setup_logs_channel", description="Seleciona o canal de logs e cria o sistema (apenas dono)")
@app_commands.describe(canal="Canal onde os membros poderão ver as logs")
async def setup_logs_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono do servidor** pode usar este comando!", ephemeral=True)
        return

    cfg = get_cfg(interaction.guild.id)
    cfg["logs_channel_id"] = canal.id

    await interaction.response.send_message(
        f"✅ Canal **{canal.mention}** selecionado como canal de logs!\n"
        f"⚙️ Criando canal de verificação...",
        ephemeral=True
    )

    await create_verification_channel(interaction.guild, interaction.user, canal)


async def create_verification_channel(guild: discord.Guild, owner: discord.Member, logs_channel=None):
    """Cria o canal de verificação e envia o painel."""
    cfg = get_cfg(guild.id)

    # Permissões do canal de verificação: todos os membros podem ver, não enviar
    member_role = discord.utils.get(guild.roles, name="👤 Membro")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            read_messages=True,
            send_messages=False,
            read_message_history=True,
            add_reactions=True
        ),
    }
    if member_role:
        overwrites[member_role] = discord.PermissionOverwrite(
            read_messages=True,
            send_messages=False,
            read_message_history=True,
            add_reactions=True
        )
    if guild.owner:
        overwrites[guild.owner] = discord.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            manage_messages=True
        )

    # Criar ou pegar canal existente
    verify_ch = discord.utils.get(guild.text_channels, name="「🔍」verificação-logs")
    if not verify_ch:
        # Tentar criar em uma categoria relevante
        cat = discord.utils.get(guild.categories, name="┣━━ 📊 USER LOGS ━━┫")
        verify_ch = await guild.create_text_channel(
            "「🔍」verificação-logs",
            category=cat,
            overwrites=overwrites,
            topic="Canal de verificação de logs • Sistema automático"
        )

    cfg["verify_channel_id"] = verify_ch.id

    # Enviar painel de verificação
    embed = discord.Embed(
        title="🔍 Verificação de Logs",
        description=(
            "**Bem-vindo ao Sistema de Verificação de Logs!**\n\n"
            "Para verificar sua conta e ter acesso ao canal de logs, clique no botão abaixo.\n\n"
            "⚠️ **Importante:**\n"
            "• Você precisará do seu **nome de usuário do Roblox**\n"
            "• O processo é simples e rápido\n"
            "• Um canal privado será criado para você\n\n"
            "🔒 Apenas você e o dono poderão ver o canal criado."
        ),
        color=0x5865F2
    )
    embed.set_image(url=IMG_VERIFICACAO)
    embed.set_footer(text=f"{guild.name} • Sistema de Verificação")

    bot2.add_view(VerifyPanelView(guild.id))
    await verify_ch.send(embed=embed, view=VerifyPanelView(guild.id))

    # Notificar dono
    try:
        confirm_embed = discord.Embed(
            title="✅ Sistema Configurado!",
            description=f"Canal de verificação criado: {verify_ch.mention}\n\nO painel de verificação está pronto!",
            color=0x43b581
        )
        await owner.send(embed=confirm_embed)
    except Exception:
        pass


# ============================================================
# VIEW: Painel de Verificação (no canal de verificação)
# ============================================================
class VerifyPanelView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="Verificar Conta", emoji="🔍", style=discord.ButtonStyle.blurple, custom_id="verify_start")
    async def verify_start(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            guild = bot2.get_guild(self.guild_id)

        # Verificar se já tem canal privado aberto
        for ch_id, info in private_channels.items():
            if info.get("opener_id") == interaction.user.id and info.get("guild_id") == guild.id and not info.get("closed"):
                ch = guild.get_channel(ch_id)
                if ch:
                    await interaction.response.send_message(f"❌ Você já tem um canal de verificação aberto: {ch.mention}", ephemeral=True)
                    return

        await interaction.response.send_message("⏳ Criando seu canal privado...", ephemeral=True)
        await create_private_verify_channel(guild, interaction.user)


async def create_private_verify_channel(guild: discord.Guild, member: discord.Member):
    """Cria canal privado para verificação do membro."""
    cfg = get_cfg(guild.id)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
            read_message_history=True, add_reactions=True
        ),
    }
    if guild.owner:
        overwrites[guild.owner] = discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
            manage_messages=True, manage_channels=True
        )

    # Criar em categoria de logs se existir
    cat = discord.utils.get(guild.categories, name="┣━━ 📊 USER LOGS ━━┫")
    ch_name = f"verify-{member.name[:15]}".lower().replace(" ", "-")

    try:
        private_ch = await guild.create_text_channel(
            ch_name,
            category=cat,
            overwrites=overwrites,
            topic=f"Canal de verificação de {member.display_name}"
        )
    except Exception as e:
        print(f"Erro ao criar canal privado: {e}")
        return

    # Registrar canal
    private_channels[private_ch.id] = {
        "opener_id": member.id,
        "guild_id": guild.id,
        "opened_at": datetime.datetime.utcnow(),
        "assumed": False,
        "closed": False,
        "roblox_username": None,
        "logs_channel_id": cfg.get("logs_channel_id"),
    }

    # Enviar mensagem inicial no canal privado
    embed = discord.Embed(
        title="🔍 Verificação de Conta Roblox",
        description=(
            f"Olá {member.mention}!\n\n"
            "Para completar a verificação, precisamos do seu **nome de usuário do Roblox**.\n\n"
            "**Instruções:**\n"
            "1️⃣ Clique em **Inserir Username** abaixo\n"
            "2️⃣ Digite seu nome de usuário do Roblox\n"
            "3️⃣ Confirme que é o perfil correto\n\n"
            "⏰ Este canal fechará automaticamente após **9 horas** sem interação.\n"
            "✅ Após confirmado, você receberá o cargo em **1 hora** o canal fecha."
        ),
        color=0x5865F2
    )
    embed.set_footer(text=f"{guild.name} • Verificação")

    # View com botão do membro e do dono
    view = PrivateChannelView(member.id, guild.id)
    await private_ch.send(content=f"{member.mention}", embed=embed, view=view)

    # Notificar dono via DM
    if guild.owner:
        try:
            owner_embed = discord.Embed(
                title="🔔 Nova Verificação Iniciada",
                description=f"**Membro:** {member.mention} (`{member}`)\n**Canal:** {private_ch.mention}",
                color=0xffa500,
                timestamp=datetime.datetime.utcnow()
            )
            owner_view = OwnerPrivateChannelView(private_ch.id, guild.id)
            await guild.owner.send(embed=owner_embed, view=owner_view)
        except Exception:
            pass


# ============================================================
# VIEW: Canal Privado — Botões do Membro e Dono
# ============================================================
class PrivateChannelView(discord.ui.View):
    def __init__(self, opener_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id
        self.guild_id = guild_id

    @discord.ui.button(label="Inserir Username", emoji="📝", style=discord.ButtonStyle.blurple, custom_id="insert_username")
    async def insert_username(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Apenas o membro que abriu pode usar
        if interaction.user.id != self.opener_id:
            await interaction.response.send_message("❌ Apenas quem abriu este canal pode usar este botão!", ephemeral=True)
            return

        # Mostrar modal para inserir username
        modal = RobloxUsernameModal(self.opener_id, self.guild_id, interaction.channel.id)
        await interaction.response.send_modal(modal)


class RobloxUsernameModal(discord.ui.Modal, title="Inserir Nome de Usuário Roblox"):
    username = discord.ui.TextInput(
        label="Nome de Usuário do Roblox",
        placeholder="Ex: Builderman",
        min_length=3,
        max_length=20,
        required=True
    )

    def __init__(self, opener_id: int, guild_id: int, channel_id: int):
        super().__init__()
        self.opener_id = opener_id
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        roblox_name = self.username.value.strip()

        await interaction.followup.send(f"🔍 Buscando perfil **{roblox_name}** no Roblox...", ephemeral=True)

        # Buscar perfil no Roblox via API
        profile_data = await search_roblox_user(roblox_name)

        channel = interaction.guild.get_channel(self.channel_id) if interaction.guild else bot2.get_channel(self.channel_id)
        if not channel:
            return

        if not profile_data:
            embed = discord.Embed(
                title="❌ Usuário não encontrado",
                description=f"Não encontrei o usuário **{roblox_name}** no Roblox.\nVerifique o nome e tente novamente.",
                color=0xf04747
            )
            await channel.send(embed=embed)
            return

        # Salvar username temporariamente
        if self.channel_id in private_channels:
            private_channels[self.channel_id]["roblox_username"] = roblox_name
            private_channels[self.channel_id]["roblox_id"] = profile_data.get("id")
            private_channels[self.channel_id]["roblox_display"] = profile_data.get("displayName", roblox_name)

        # Montar embed de confirmação
        avatar_url = profile_data.get("avatar_url", "")
        embed = discord.Embed(
            title="🎮 Perfil Encontrado — Este é você?",
            description=(
                f"**Username:** `{profile_data.get('name', roblox_name)}`\n"
                f"**Display Name:** {profile_data.get('displayName', roblox_name)}\n"
                f"**ID:** `{profile_data.get('id', 'N/A')}`\n"
                f"**Descrição:** {profile_data.get('description', 'Sem descrição')[:100]}\n\n"
                "Se for você, clique em **Confirmar** para receber o cargo!"
            ),
            color=0x43b581
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embed.set_footer(text="Apenas você pode confirmar")

        opener = interaction.guild.get_member(self.opener_id) if interaction.guild else None
        view = ConfirmProfileView(self.opener_id, self.guild_id, self.channel_id)
        msg = await channel.send(content=f"{opener.mention if opener else ''}", embed=embed, view=view)


async def search_roblox_user(username: str):
    """Busca usuário no Roblox via API oficial."""
    try:
        async with aiohttp.ClientSession() as session:
            # API de busca por username
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {"usernames": [username], "excludeBannedUsers": False}
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                users = data.get("data", [])
                if not users:
                    return None
                user = users[0]
                user_id = user.get("id")

            # Buscar detalhes do usuário
            async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
                if resp.status != 200:
                    return None
                user_data = await resp.json()

            # Buscar avatar
            avatar_url = None
            async with session.get(
                f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png"
            ) as resp:
                if resp.status == 200:
                    thumb_data = await resp.json()
                    thumb_list = thumb_data.get("data", [])
                    if thumb_list:
                        avatar_url = thumb_list[0].get("imageUrl")

            user_data["avatar_url"] = avatar_url
            return user_data
    except Exception as e:
        print(f"Erro ao buscar Roblox: {e}")
        return None


# ============================================================
# VIEW: Confirmar Perfil Roblox
# ============================================================
class ConfirmProfileView(discord.ui.View):
    def __init__(self, opener_id: int, guild_id: int, channel_id: int):
        super().__init__(timeout=300)
        self.opener_id = opener_id
        self.guild_id = guild_id
        self.channel_id = channel_id

    @discord.ui.button(label="Confirmar — Sou eu!", emoji="✅", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opener_id:
            await interaction.response.send_message("❌ Apenas quem abriu este canal pode confirmar!", ephemeral=True)
            return

        await interaction.response.defer()

        guild = bot2.get_guild(self.guild_id)
        if not guild:
            return

        cfg = get_cfg(self.guild_id)
        ch_info = private_channels.get(self.channel_id, {})
        logs_ch_id = ch_info.get("logs_channel_id") or cfg.get("logs_channel_id")

        # Dar cargo 📊 User Logs
        user_logs_role = discord.utils.get(guild.roles, name="📊 User Logs")
        member = guild.get_member(self.opener_id)
        channel = guild.get_channel(self.channel_id)

        role_given = False
        if member and user_logs_role:
            try:
                await member.add_roles(user_logs_role, reason="Verificação Roblox confirmada")
                role_given = True
            except Exception as e:
                print(f"Erro ao dar cargo: {e}")

        # Se tiver canal de logs configurado, ajustar permissões
        if logs_ch_id:
            logs_ch = guild.get_channel(logs_ch_id)
            if logs_ch and member:
                try:
                    await logs_ch.set_permissions(member,
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True,
                        add_reactions=True,
                        use_external_emojis=True,
                        use_external_stickers=True
                    )
                except Exception as e:
                    print(f"Erro ao definir permissões no canal de logs: {e}")

        # Mensagem de sucesso
        roblox_name = ch_info.get("roblox_username", "N/A")
        embed = discord.Embed(
            title="✅ Verificação Concluída!",
            description=(
                f"{member.mention if member else 'Membro'}, sua conta foi verificada!\n\n"
                f"**Roblox:** `{roblox_name}`\n"
                f"**Cargo:** {'📊 User Logs ✅' if role_given else '⚠️ Cargo não encontrado'}\n\n"
                f"⏰ Este canal será fechado em **1 hora**."
            ),
            color=0x43b581
        )
        await interaction.channel.send(embed=embed)

        # Desabilitar botões
        self.confirm.disabled = True
        self.confirm.label = "Confirmado ✅"
        await interaction.message.edit(view=self)

        # Fechar canal após 1 hora
        await asyncio.sleep(3600)
        if self.channel_id in private_channels:
            private_channels[self.channel_id]["closed"] = True
        try:
            ch = guild.get_channel(self.channel_id)
            if ch:
                await ch.delete(reason="Verificação concluída — 1 hora de espera")
        except Exception:
            pass


# ============================================================
# VIEW: Botão do Dono (enviado por DM)
# ============================================================
class OwnerPrivateChannelView(discord.ui.View):
    def __init__(self, channel_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.guild_id = guild_id

    @discord.ui.select(
        placeholder="Selecione uma ação...",
        custom_id="owner_action_select",
        options=[
            discord.SelectOption(label="Assumir", emoji="✅", description="Impede o fechamento automático por inatividade", value="assume"),
            discord.SelectOption(label="Fechar Canal", emoji="🔒", description="Fecha o canal em 6 segundos", value="close"),
        ]
    )
    async def owner_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild = bot2.get_guild(self.guild_id)
        if not guild or interaction.user.id != guild.owner_id:
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return

        action = select.values[0]
        ch_info = private_channels.get(self.channel_id)
        ch = guild.get_channel(self.channel_id)

        if action == "assume":
            if ch_info:
                ch_info["assumed"] = True
            embed = discord.Embed(
                title="✅ Canal Assumido",
                description=f"O canal {'`'+ch.name+'`' if ch else str(self.channel_id)} não será fechado automaticamente por inatividade.",
                color=0x43b581
            )
            await interaction.response.edit_message(embed=embed, view=None)
            if ch:
                notify_embed = discord.Embed(
                    title="👑 Dono Assumiu",
                    description="O dono do servidor assumiu este canal. Ele não fechará por inatividade.",
                    color=0xffd700
                )
                await ch.send(embed=notify_embed)

        elif action == "close":
            embed = discord.Embed(
                title="🔒 Fechando Canal...",
                description=f"O canal será fechado em **6 segundos**.",
                color=0xf04747
            )
            await interaction.response.edit_message(embed=embed, view=None)
            await asyncio.sleep(6)
            if ch:
                try:
                    await ch.send("🔒 Canal fechado pelo dono do servidor.")
                    await asyncio.sleep(2)
                    await ch.delete(reason="Fechado pelo dono do servidor")
                except Exception:
                    pass
            if self.channel_id in private_channels:
                private_channels[self.channel_id]["closed"] = True


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Painel Web Bot 2 rodando em http://0.0.0.0:8081")
    bot2.run(TOKEN)
