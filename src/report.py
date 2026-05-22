"""
Gera o relatório diário de benchmark dos concorrentes.
"""

import os
import logging
import requests
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

TYPE_LABEL = {
    "reel": "Reel",
    "carrossel": "Carrossel",
    "imagem": "Imagem",
}


class ReportGenerator:
    def generate(self, data: dict[str, list[dict]], date_str: str = None) -> str:
        if date_str:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

        date_label = target_date.strftime("%d/%m/%Y")
        all_day_posts = {}
        total_posts_day = 0

        for username, posts in data.items():
            day_posts = [
                p for p in posts
                if p.get("published_at") and p["published_at"].date() == target_date
            ]
            all_day_posts[username] = sorted(day_posts, key=lambda p: p["engagement"], reverse=True)
            total_posts_day += len(day_posts)

        lines = []
        lines.append(f"*BENCHMARK DIÁRIO — {date_label}*")
        lines.append("")

        perfis_com_posts = {u: p for u, p in all_day_posts.items() if p}
        todos_posts = [p for posts in perfis_com_posts.values() for p in posts]

        # 1. Sugestão de pauta no topo
        if todos_posts:
            sugestao = self._gerar_sugestao_pauta(todos_posts, perfis_com_posts, date_label)
            if sugestao:
                lines.append("*SUGESTÃO DE PAUTA — D+1*")
                lines.append(sugestao)
                lines.append("")
                lines.append("─────────────────────")
                lines.append("")

        # 2. Comparativo por perfil
        lines.append("*COMPARATIVO DO DIA*")
        lines.append("")

        if not perfis_com_posts:
            lines.append("Nenhum perfil postou no D-1.")
        else:
            for username, posts in perfis_com_posts.items():
                total_likes = sum(p["likes"] for p in posts)
                total_comments = sum(p["comments"] for p in posts)
                total_views = sum(p["views"] for p in posts if p.get("views"))
                n = len(posts)
                tipos = {}
                for p in posts:
                    tipos[p["type"]] = tipos.get(p["type"], 0) + 1
                tipo_str = ", ".join(f"{v} {TYPE_LABEL.get(k, k)}" for k, v in tipos.items())

                top = posts[0]
                hora = top["published_at"].strftime("%H:%M") if top["published_at"] else "—"

                lines.append(f"@{username}")
                lines.append(f"  {n} post(s) — {tipo_str}")
                lines.append(f"  Curtidas: {total_likes:,}  Comentários: {total_comments:,}" + (f"  Views: {total_views:,}" if total_views else ""))
                lines.append(f"  Melhor horário: {hora}h — {TYPE_LABEL.get(top['type'], top['type'])}")
                lines.append(f"  {top['url']}")
                lines.append("")

        # 3. Ranking por engajamento total
        if perfis_com_posts:
            lines.append("─────────────────────")
            lines.append("")
            lines.append("*RANKING DE ENGAJAMENTO*")
            ranking = sorted(
                perfis_com_posts.items(),
                key=lambda x: sum(p["engagement"] for p in x[1]),
                reverse=True
            )
            for i, (username, posts) in enumerate(ranking, 1):
                eng = sum(p["engagement"] for p in posts)
                lines.append(f"  {i}. @{username} — {eng:,} interações")

        lines.append("")
        lines.append(f"_{total_posts_day} post(s) monitorado(s) | Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}_")

        return "\n".join(lines)

    def _gerar_sugestao_pauta(self, posts: list[dict], perfis: dict, date_label: str) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY não definida — sugestão de pauta desativada.")
            return ""

        # Monta resumo por perfil com horário e formato campeão
        resumo_perfis = []
        for username, day_posts in perfis.items():
            if not day_posts:
                continue
            top = day_posts[0]
            hora = top["published_at"].strftime("%H:%M") if top["published_at"] else "—"
            resumo_perfis.append(
                f"- @{username}: melhor post foi {top['type']} às {hora}h "
                f"com {top['likes']} curtidas e {top['comments']} comentários"
                + (f" e {top['views']} views" if top.get("views") else "")
            )

        resumo_top = []
        for p in sorted(posts, key=lambda x: x["engagement"], reverse=True)[:8]:
            hora = p["published_at"].strftime("%H:%M") if p.get("published_at") else "—"
            resumo_top.append(
                f"- @{p['username']} | {p['type']} | {hora}h | "
                f"{p['likes']} curtidas {p['comments']} comentários"
                + (f" {p['views']} views" if p.get("views") else "")
                + (f" | \"{p['caption'][:70]}\"" if p.get("caption") else "")
            )

        prompt = f"""Você é um estrategista de conteúdo para Instagram especializado em empreendedorismo e negócios.

Dados dos concorrentes no dia {date_label}:

Resumo por perfil:
{chr(10).join(resumo_perfis)}

Top posts do dia:
{chr(10).join(resumo_top)}

Com base nesses dados, escreva uma sugestão de pauta personalizada por perfil. Para cada perfil diga exatamente: "@perfil seu melhor horário para postar é X horas com [formato], sugerimos [tema/gancho]."

Responda em português, direto, sem introduções, um perfil por linha. Máximo 150 palavras."""

        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Erro ao gerar sugestão de pauta: {e}")
            return ""