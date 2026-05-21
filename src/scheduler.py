"""
Agendador para rodar o pipeline 1x por dia no horário configurado.
"""

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, collector, generator, sender, profiles: list[str]):
        self.collector = collector
        self.generator = generator
        self.sender = sender
        self.profiles = profiles
        self.running = False

    async def start(self, time_str: str, recipient: str):
        """
        Inicia o loop de agendamento.
        time_str: horário no formato "HH:MM", ex: "07:00"
        """
        self.running = True
        hour, minute = map(int, time_str.split(":"))
        logger.info(f"Agendador iniciado — pipeline rodará todos os dias às {time_str}.")

        while self.running:
            now = datetime.now()
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Se o horário de hoje já passou, agenda para amanhã
            if next_run <= now:
                next_run += timedelta(days=1)

            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"Próxima execução: {next_run.strftime('%d/%m/%Y às %H:%M')} ({wait_seconds:.0f}s)")

            await asyncio.sleep(wait_seconds)

            if self.running:
                await self._run_pipeline(recipient)

    async def _run_pipeline(self, recipient: str):
        """Executa o pipeline completo: coleta → relatório → envio."""
        logger.info("⏰ Iniciando pipeline agendado...")
        try:
            data = await self.collector.collect(self.profiles, max_posts=20)
            report = self.generator.generate(data)
            success = await self.sender.send(recipient, report)
            if success:
                logger.info("✅ Pipeline concluído com sucesso.")
            else:
                logger.error("❌ Pipeline concluído, mas falha no envio do WhatsApp.")
        except Exception as e:
            logger.error(f"❌ Erro no pipeline agendado: {e}", exc_info=True)

    def stop(self):
        self.running = False
        logger.info("Agendador parado.")