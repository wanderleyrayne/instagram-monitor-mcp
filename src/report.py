"""
Gera o relatório diário de benchmark dos concorrentes.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

TYPE_EMOJI = {
    "reel": "🎬",
    "carrossel": "🎠",
    "imagem": "🖼️",
}


class ReportGenerator:
    def generate(self, data: dict[str, list[dict]], date_str: str = None) -> str:
        """
        Gera o relatório completo para D-1 (ou a data informada).
        data: { username: [posts] }
        """
        if date_str:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

        date_label = target_date.strftime("%d/%m/%Y")
        lines = []

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 *BENCHMARK DIÁRIO — {date_label}*")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")

        total_posts_day = 0

        for username, posts in data.items():
            # Filtra apenas posts do D-1
            day_posts = [
                p for p in posts
                if p.get("published_at") and p["published_at"].date() == target_date
            ]

            lines.append(f"👤 *@{username}*")

            if not day_posts:
                lines.append("   _Sem posts no D-1._")
                lines.append("")
                continue

            total_posts_day += len(day_posts)

            # Ordena por engajamento (maior primeiro)
            day_posts_sorted = sorted(day_posts, key=lambda p: p["engagement"], reverse=True)

            for i, post in enumerate(day_posts_sorted, 1):
                emoji = TYPE_EMOJI.get(post["type"], "📄")
                pub_time = post["published_at"].strftime("%H:%M") if post["published_at"] else "—"

                lines.append(f"   {i}. {emoji} *{post['type'].upper()}* — {pub_time}h")
                lines.append(f"      ❤️ {post['likes']}  💬 {post['comments']}" + (f"  👁️ {post['views']}" if post["views"] else ""))

                if post["caption"]:
                    caption_preview = post["caption"][:150].replace("\n", " ")
                    lines.append(f"      📝 _{caption_preview}_")

                lines.append(f"      🔗 {post['url']}")
                lines.append("")

        if total_posts_day == 0:
            lines.append("ℹ️ Nenhum dos perfis monitorados postou no D-1.")
        else:
            lines.append(f"📌 *Total: {total_posts_day} post(s) publicado(s) no D-1*")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"_Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}_")

        return "\n".join(lines)