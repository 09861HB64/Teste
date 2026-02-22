"""
main_runner.py — Liga Bot 1 e Bot 2 simultaneamente

Variáveis de ambiente necessárias:
  DISCORD_TOKEN_BOT1  → Token do Bot 1 (servidor principal)
  DISCORD_TOKEN_BOT2  → Token do Bot 2 (sistema de logs/verificação)

Execute: python main_runner.py
"""

import asyncio
import os
import subprocess
import sys
from threading import Thread

def run_bot1():
    """Roda bot1_main.py em processo separado."""
    print("🚀 Iniciando Bot 1...")
    subprocess.run([sys.executable, "bot1_main.py"])

def run_bot2():
    """Roda bot2_logs.py em processo separado."""
    print("🚀 Iniciando Bot 2...")
    subprocess.run([sys.executable, "bot2_logs.py"])

if __name__ == "__main__":
    # Verificar tokens
    token1 = os.environ.get("DISCORD_TOKEN_BOT1")
    token2 = os.environ.get("DISCORD_TOKEN_BOT2")

    if not token1:
        print("❌ ERRO: Variável DISCORD_TOKEN_BOT1 não definida!")
        sys.exit(1)
    if not token2:
        print("❌ ERRO: Variável DISCORD_TOKEN_BOT2 não definida!")
        sys.exit(1)

    print("=" * 50)
    print("  🤖 Iniciando os 2 Bots do Discord")
    print("  Bot 1 → Porta 8080 (Servidor)")
    print("  Bot 2 → Porta 8081 (Logs/Verificação)")
    print("=" * 50)

    # Criar threads para rodar os dois bots simultaneamente
    t1 = Thread(target=run_bot1, daemon=False, name="Bot1")
    t2 = Thread(target=run_bot2, daemon=False, name="Bot2")

    t1.start()
    t2.start()

    print("✅ Ambos os bots iniciados!")
    print("📊 Dashboard Bot 1: http://localhost:8080")
    print("📊 Dashboard Bot 2: http://localhost:8081")

    t1.join()
    t2.join()
