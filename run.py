"""
Script para rodar o pipeline diretamente sem precisar de um MCP client.
Útil para testes e para configurar um cron job.

Uso:
    python run.py                    # Gera e envia o relatório D-1
    python run.py --dry-run          # Gera o relatório mas NÃO envia
    python run.py --date 2025-01-20  # Relatório de uma data específica
    python run.py --schedule 07:00   # Inicia o agendador (roda para sempre)
"""

import asyncio
import argparse
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROFILES = [
    "umantoniodasilva",
    "marcusmarquesoficial",
    "jcsemenzato",
    "raphaeldmattos",
    "reinaldozanon",
]


async def main():
    parser = argparse.ArgumentParser(description="Instagram Monitor — Pipeline Diário")
    parser.add_argument("--dry-run", action="store_true", help="Gera o relatório sem enviar no WhatsApp")
    parser.add_argument("--date", type=str, help="Data no formato YYYY-MM-DD (padrão: D-1)")
    parser.add_argument("--schedule", type=str, metavar="HH:MM", help="Inicia o agendador nesse horário diário")
    args = parser.parse_args()

    # Importa aqui para garantir que .env já foi carregado
    from src.instagram import InstagramCollector
    from src.report import ReportGenerator
    from src.whatsapp import WhatsAppSender
    from src.scheduler import Scheduler

    collector = InstagramCollector()
    generator = ReportGenerator()

    if args.schedule:
        recipient = os.getenv("WHATSAPP_RECIPIENT")
        if not recipient:
            logger.error("Defina WHATSAPP_RECIPIENT no .env para usar o agendador.")
            return
        sender = WhatsAppSender()
        scheduler = Scheduler(collector, generator, sender, PROFILES)
        await scheduler.start(args.schedule, recipient)
        return

    # Pipeline único
    logger.info("Coletando posts...")
    data = await collector.collect(PROFILES, max_posts=20)

    logger.info("Gerando relatório...")
    report = generator.generate(data, args.date)

    print("\n" + "=" * 50)
    print(report)
    print("=" * 50 + "\n")

    if args.dry_run:
        logger.info("--dry-run ativo: relatório NÃO enviado ao WhatsApp.")
        return

    recipient = os.getenv("WHATSAPP_RECIPIENT")
    if not recipient:
        logger.warning("WHATSAPP_RECIPIENT não definido. Relatório exibido apenas no terminal.")
        return

    sender = WhatsAppSender()
    logger.info(f"Enviando relatório para {recipient}...")
    success = await sender.send(recipient, report)

    if success:
        logger.info("✅ Relatório enviado com sucesso!")
    else:
        logger.error("❌ Falha ao enviar o relatório.")


if __name__ == "__main__":
    asyncio.run(main())