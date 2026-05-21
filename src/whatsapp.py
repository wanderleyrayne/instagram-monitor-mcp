"""
Envio de mensagens WhatsApp via Z-API.
Docs: https://developer.z-api.io
"""

import os
import logging
import aiohttp

logger = logging.getLogger(__name__)

# Limite de caracteres por mensagem do WhatsApp
WHATSAPP_MAX_LENGTH = 4000


class WhatsAppSender:
    def __init__(self):
        self.instance_id = os.getenv("ZAPI_INSTANCE_ID")
        self.token = os.getenv("ZAPI_TOKEN")
        self.client_token = os.getenv("ZAPI_CLIENT_TOKEN")  # Security token do painel Z-API

        if not self.instance_id or not self.token:
            raise ValueError("ZAPI_INSTANCE_ID e ZAPI_TOKEN devem estar definidos no .env")

        self.base_url = f"https://api.z-api.io/instances/{self.instance_id}/token/{self.token}"

    async def send(self, recipient: str, text: str) -> bool:
        """
        Envia uma mensagem de texto para um número ou grupo do WhatsApp.
        Se o texto for muito longo, divide em partes automaticamente.
        recipient: número no formato 5521999999999 ou ID do grupo
        """
        parts = self._split_message(text)
        logger.info(f"Enviando {len(parts)} parte(s) para {recipient}...")

        async with aiohttp.ClientSession() as session:
            for i, part in enumerate(parts, 1):
                success = await self._send_part(session, recipient, part)
                if not success:
                    logger.error(f"Falha ao enviar parte {i}/{len(parts)}")
                    return False
                logger.info(f"  → Parte {i}/{len(parts)} enviada com sucesso.")

        return True

    async def _send_part(self, session: aiohttp.ClientSession, recipient: str, text: str) -> bool:
        url = f"{self.base_url}/send-text"

        headers = {"Content-Type": "application/json"}
        if self.client_token:
            headers["Client-Token"] = self.client_token

        payload = {
            "phone": recipient,
            "message": text,
        }

        try:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                body = await resp.json()
                if resp.status in (200, 201) and body.get("zaapId") or body.get("messageId"):
                    return True
                logger.error(f"Z-API retornou {resp.status}: {body}")
                return False
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão com Z-API: {e}")
            return False

    def _split_message(self, text: str) -> list[str]:
        """Divide mensagens longas em partes respeitando o limite do WhatsApp."""
        if len(text) <= WHATSAPP_MAX_LENGTH:
            return [text]

        parts = []
        while text:
            if len(text) <= WHATSAPP_MAX_LENGTH:
                parts.append(text)
                break
            cut = text.rfind("\n", 0, WHATSAPP_MAX_LENGTH)
            if cut == -1:
                cut = WHATSAPP_MAX_LENGTH
            parts.append(text[:cut])
            text = text[cut:].lstrip("\n")

        return parts