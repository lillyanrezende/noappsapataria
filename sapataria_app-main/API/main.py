from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError
import logging
import sys
import os
from pathlib import Path

# Adiciona o diretório pai ao path para importar db e services
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

# Importa models do diretório API atual
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

from models import WooCommerceOrderWebhook
from db import DB
from services import ProductService

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sapataria-api")

app = FastAPI(
    title="API Integração Sapataria - WooCommerce Webhook",
    version="0.1.0",
    description="Recebe webhooks de novas vendas do WooCommerce e baixa estoque"
)

# Instâncias globais
db = DB()
product_service = ProductService(db)

@app.post("/venda/woocommerce")
async def webhook_woocommerce(request: Request):
    """
    Endpoint que recebe o webhook de 'Order Created' do WooCommerce.
    Extrai GTIN do SKU ou meta_data e baixa o estoque no PostgreSQL.
    """
    payload = None
    content_type = (request.headers.get("content-type") or "").lower()

    try:
        if "application/json" in content_type:
            payload = await request.json()
        elif "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            payload = dict(form)
        else:
            body = await request.body()
            if body:
                try:
                    payload = await request.json()
                except Exception:
                    payload = {"raw": body.decode("utf-8", errors="ignore")}

        logger.info(f"Webhook recebido - Content-Type: {content_type}")
        logger.info(f"Payload completo: {payload}")

        # WooCommerce pode enviar apenas webhook_id no teste
        if isinstance(payload, dict) and set(payload.keys()) == {"webhook_id"}:
            return {"ok": True, "mensagem": "Webhook de teste recebido"}

        # Valida o payload com o modelo Pydantic
        order = WooCommerceOrderWebhook(**(payload or {}))
    except ValidationError as e:
        logger.error(f"Erro de validação no payload: {e}")
        logger.error(f"Payload recebido: {payload}")
        raise HTTPException(status_code=422, detail=f"Payload inválido: {str(e)}")
    except Exception as e:
        logger.error(f"Erro ao processar payload: {e}")
        raise HTTPException(status_code=400, detail=f"Erro: {str(e)}")

    if order.status not in ["processing", "completed"]:
        logger.info(f"Ignorando order {order.id} - status: {order.status}")
        return {"ok": True, "mensagem": "Status não processável"}

    processed_items = 0

    for item in order.line_items:
        gtin = None

        # Prioridade 1: tenta pegar GTIN do campo SKU da variação
        if item.sku and item.sku.strip():
            gtin = item.sku.strip()

        # Prioridade 2: tenta achar em meta_data (caso o cliente use custom field "_gtin" ou "gtin")
        if not gtin:
            for meta in item.meta_data:
                if meta.key in ["_gtin", "gtin", "ean", "upc"]:
                    gtin = str(meta.value).strip()
                    break

        if not gtin:
            logger.warning(f"Item sem GTIN identificável: {item.name} (variation_id: {item.variation_id})")
            continue

        try:
            # Aqui tu baixa o estoque usando o serviço que já tens
            # Ajusta o método conforme o teu ProductService
            sucesso, mensagem = product_service.sell_from_woocommerce(gtin, item.quantity)

            if sucesso:
                processed_items += 1
                logger.info(f"Baixa de estoque OK - GTIN: {gtin}, Qtd: {item.quantity}")
            else:
                logger.error(f"Falha na baixa - GTIN: {gtin} - {mensagem}")
                # Pode decidir se continua processando os outros itens ou para tudo
                # Aqui continua, mas avisa

        except Exception as e:
            logger.exception(f"Erro ao processar item {gtin}: {str(e)}")
            continue

    if processed_items == 0:
        return {"ok": True, "mensagem": "Nenhum item com GTIN válido encontrado"}

    return {
        "ok": True,
        "mensagem": f"Processados {processed_items} de {len(order.line_items)} itens com sucesso"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sapataria-webhook"}