"""
Instagram Monitor MCP Server
Coleta posts de perfis do Instagram e envia relatório diário no WhatsApp.
"""

import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from typing import Any

from src.instagram import InstagramCollector
from src.report import ReportGenerator
from src.whatsapp import WhatsAppSender
from src.scheduler import Scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Server("instagram-monitor")

PROFILES = [
    "umantoniodasilva",
    "marcusmarquesoficial",
    "jcsemenzato",
    "raphaeldmattos",
    "reinaldozanon",
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="collect_posts",
            description="Coleta os posts recentes dos perfis monitorados do Instagram.",
            inputSchema={
                "type": "object",
                "properties": {
                    "profiles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de usernames do Instagram. Usa os padrões se omitido.",
                    },
                    "max_posts": {
                        "type": "integer",
                        "description": "Máximo de posts por perfil (padrão: 20).",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="generate_report",
            description="Gera o relatório diário de benchmark dos concorrentes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Data do relatório no formato YYYY-MM-DD. Usa D-1 se omitido.",
                    }
                },
            },
        ),
        Tool(
            name="send_whatsapp",
            description="Envia o relatório gerado via WhatsApp.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_text": {
                        "type": "string",
                        "description": "Texto do relatório a ser enviado.",
                    },
                    "recipient": {
                        "type": "string",
                        "description": "Número ou ID do grupo WhatsApp.",
                    },
                },
                "required": ["report_text", "recipient"],
            },
        ),
        Tool(
            name="run_daily_pipeline",
            description="Executa o pipeline completo: coleta → relatório → envio WhatsApp.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Número ou ID do grupo WhatsApp para receber o relatório.",
                    }
                },
                "required": ["recipient"],
            },
        ),
        Tool(
            name="start_scheduler",
            description="Inicia o agendador para rodar o pipeline 1x por dia automaticamente.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": "Horário de execução no formato HH:MM (ex: '07:00'). Padrão: 07:00.",
                        "default": "07:00",
                    },
                    "recipient": {
                        "type": "string",
                        "description": "Número ou ID do grupo WhatsApp.",
                    },
                },
                "required": ["recipient"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    collector = InstagramCollector()
    generator = ReportGenerator()
    sender = WhatsAppSender()

    if name == "collect_posts":
        profiles = arguments.get("profiles", PROFILES)
        max_posts = arguments.get("max_posts", 20)

        logger.info(f"Coletando posts de {len(profiles)} perfis...")
        data = await collector.collect(profiles, max_posts)
        total = sum(len(posts) for posts in data.values())
        return [TextContent(type="text", text=f"✅ Coletados {total} posts de {len(profiles)} perfis.\n\n{_summarize_collection(data)}")]

    elif name == "generate_report":
        date = arguments.get("date")
        logger.info(f"Gerando relatório para {date or 'D-1'}...")
        profiles = arguments.get("profiles", PROFILES)
        data = await collector.collect(profiles, max_posts=20)
        report = generator.generate(data, date)
        return [TextContent(type="text", text=report)]

    elif name == "send_whatsapp":
        report_text = arguments["report_text"]
        recipient = arguments["recipient"]
        logger.info(f"Enviando relatório para {recipient}...")
        success = await sender.send(recipient, report_text)
        status = "✅ Relatório enviado com sucesso!" if success else "❌ Falha ao enviar o relatório."
        return [TextContent(type="text", text=status)]

    elif name == "run_daily_pipeline":
        recipient = arguments["recipient"]
        logger.info("Iniciando pipeline diário completo...")

        data = await collector.collect(PROFILES, max_posts=20)
        report = generator.generate(data)
        success = await sender.send(recipient, report)

        status = "✅ Pipeline concluído! Relatório enviado." if success else "⚠️ Relatório gerado, mas falha no envio WhatsApp."
        return [TextContent(type="text", text=f"{status}\n\n---\n\n{report}")]

    elif name == "start_scheduler":
        time_str = arguments.get("time", "07:00")
        recipient = arguments["recipient"]
        scheduler = Scheduler(collector, generator, sender, PROFILES)
        asyncio.create_task(scheduler.start(time_str, recipient))
        return [TextContent(type="text", text=f"⏰ Agendador iniciado! Pipeline rodará todos os dias às {time_str}.")]

    else:
        return [TextContent(type="text", text=f"❌ Ferramenta desconhecida: {name}")]


def _summarize_collection(data: dict) -> str:
    lines = []
    for profile, posts in data.items():
        lines.append(f"📸 @{profile}: {len(posts)} posts coletados")
    return "\n".join(lines)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())