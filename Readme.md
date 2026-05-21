# Instagram Monitor MCP

MCP server em Python para monitorar perfis do Instagram e enviar um relatório diário de benchmark via WhatsApp.

A ideia é simples: todo dia de manhã, o sistema coleta os posts publicados no dia anterior pelos perfis monitorados e envia um resumo no WhatsApp com engajamento e links de cada post.

## Como funciona

1. O script acessa a API do Apify para coletar os posts recentes de cada perfil
2. Filtra apenas os posts do D-1 (dia anterior)
3. Ordena por engajamento (curtidas + comentários)
4. Envia o relatório via Z-API no WhatsApp

## Pré-requisitos

- Python 3.11+
- Conta no [Apify](https://apify.com) — plano gratuito funciona
- Conta na [Z-API](https://z-api.io) com instância conectada ao WhatsApp

## Instalação

```bash
git clone https://github.com/seu-usuario/instagram-monitor-mcp.git
cd instagram-monitor-mcp

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Preencha o .env com suas credenciais
```

## Configuração

### Apify

1. Crie conta em [apify.com](https://apify.com)
2. Vá em **Settings → Integrations → API tokens**
3. Copie o token e coloque em `APIFY_API_TOKEN` no `.env`

O actor usado é o `apify~instagram-scraper` — não precisa configurar nada além do token.

### Z-API

1. Crie conta em [z-api.io](https://z-api.io)
2. Crie uma instância e escaneie o QR code com o WhatsApp
3. Copie o **ID da instância** e o **Token** em **Dados da instância web → Credenciais**
4. Ative e copie o **Client Token** em **Segurança → Token de segurança da conta**

### Arquivo `.env`

```env
# Apify
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxx

# Z-API
ZAPI_INSTANCE_ID=SEU_INSTANCE_ID
ZAPI_TOKEN=SEU_TOKEN
ZAPI_CLIENT_TOKEN=SEU_CLIENT_TOKEN

# Destinatário (DDI + DDD + número, sem símbolos)
WHATSAPP_RECIPIENT=5521999999999
```

## Como rodar

```bash
# Variável de ambiente necessária no Windows
$env:PYTHONPATH="src"  # PowerShell
export PYTHONPATH="src"  # Linux/Mac
```

Testar sem enviar no WhatsApp:
```bash
python run.py --dry-run
```

Rodar o pipeline completo:
```bash
python run.py
```

Relatório de uma data específica:
```bash
python run.py --date 2025-01-19
```

Rodar automaticamente todo dia às 07:00:
```bash
python run.py --schedule 07:00
```

Ou via cron job:
```bash
# crontab -e
0 7 * * * cd /caminho/para/instagram-monitor-mcp && .venv/bin/python run.py
```

Ferramentas disponíveis:

| Ferramenta | O que faz |
|---|---|
| `collect_posts` | Coleta posts dos perfis monitorados |
| `generate_report` | Gera o relatório do D-1 |
| `send_whatsapp` | Envia uma mensagem no WhatsApp |
| `run_daily_pipeline` | Executa o pipeline completo |
| `start_scheduler` | Inicia o agendador diário |

## Estrutura

```
instagram-monitor-mcp/
├── src/
│   ├── server.py       # MCP server
│   ├── instagram.py    # Coleta via Apify
│   ├── report.py       # Geração do relatório
│   ├── whatsapp.py     # Envio via Z-API
│   └── scheduler.py    # Agendador diário
├── run.py              # Script standalone
├── requirements.txt
├── .env.example
└── example_report.txt
```

## Perfis monitorados

- [@umantoniodasilva](https://www.instagram.com/umantoniodasilva/)
- [@marcusmarquesoficial](https://www.instagram.com/marcusmarquesoficial/)
- [@jcsemenzato](https://www.instagram.com/jcsemenzato/)
- [@raphaeldmattos](https://www.instagram.com/raphaeldmattos/)
- [@reinaldozanon](https://www.instagram.com/reinaldozanon/)

Para alterar os perfis, edite a lista `PROFILES` em `run.py` e `src/server.py`.