import os
import sys
import csv
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List, Any

import pandas as pd
import requests
from dotenv import load_dotenv


# -----------------------------
# Config: colunas do Excel
# -----------------------------
REQUIRED_COLUMNS = [
    "Ref. Keyinvoice",
    "Ref. Woocomerce",
    "Categoria",
    "Subcategoria",
    "Marca",
    "Nome",
    "Cor",
    "TAMANHO",
    "CODIGO DE BARRAS",
]

COLMAP = {
    "Ref. Keyinvoice": "ref_keyinvoice",
    "Ref. Woocomerce": "ref_woocomerce",
    "Categoria": "categoria",
    "Subcategoria": "subcategoria",
    "Marca": "marca",
    "Nome": "nome",
    "Cor": "cor",
    "TAMANHO": "tamanho",
    "CODIGO DE BARRAS": "gtin",
}


# -----------------------------
# Stats / relatório
# -----------------------------
@dataclass
class Stats:
    rows_total: int = 0
    rows_processed: int = 0        # com GTIN (tentou processar)
    rows_ok: int = 0
    rows_skipped_no_gtin: int = 0  # ignoradas porque GTIN vazio
    rows_rejected_error: int = 0   # rejeitadas por erro de validação/DB

    suppliers_created: int = 0
    brands_created: int = 0
    categories_created: int = 0
    subcategories_created: int = 0
    colors_created: int = 0
    sizes_created: int = 0

    models_created: int = 0
    models_reused: int = 0

    variants_upserted: int = 0
    stock_upserts: int = 0


# -----------------------------
# Logging
# -----------------------------
def setup_logger() -> logging.Logger:
    logger = logging.getLogger("etl")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler("etl_run.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# -----------------------------
# Helpers: limpeza/validação
# -----------------------------
def clean_str(x) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return None
    return s


def clean_gtin(x) -> Optional[str]:
    """
    Mantém só dígitos quando possível, para evitar:
    - espaços
    - hífens
    - Excel em notação científica
    """
    s = clean_str(x)
    if not s:
        return None
    s = s.replace(" ", "").replace("-", "")
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits if digits else None


def as_int_or_none(x) -> Optional[int]:
    s = clean_str(x)
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


# -----------------------------
# Supabase REST client (PostgREST)
# -----------------------------
class SupabaseClient:
    def __init__(self, supabase_url: str, supabase_key: str, dry_run: bool, logger: logging.Logger):
        self.base = supabase_url.rstrip("/") + "/rest/v1"
        self.dry_run = dry_run
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, params: dict | None = None, json: Any | None = None, prefer: str | None = None):
        url = f"{self.base}/{path.lstrip('/')}"
        headers = {}
        if prefer:
            headers["Prefer"] = prefer

        if self.dry_run and method.upper() in {"POST", "PATCH", "DELETE"}:
            self.logger.info("DRY_RUN %s %s | params=%s | json=%s", method, path, params, json)
            return []

        r = self.session.request(method, url, params=params, json=json, headers=headers, timeout=60)
        if r.status_code >= 300:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text}")
        if not r.text:
            return []
        return r.json()

    def select(self, table: str, select: str = "id", **filters) -> List[dict]:
        params = {"select": select}
        params.update(filters)
        return self._request("GET", table, params=params)

    def insert(self, table: str, rows: List[dict]) -> List[dict]:
        return self._request("POST", table, json=rows, prefer="return=representation")

    def upsert(self, table: str, rows: List[dict], on_conflict: str) -> List[dict]:
        # merge duplicates faz UPDATE quando encontra conflito
        path = f"{table}?on_conflict={on_conflict}"
        return self._request("POST", path, json=rows, prefer="return=representation,resolution=merge-duplicates")


# -----------------------------
# DB: get/create com cache (agora via Supabase)
# -----------------------------
def get_or_create_simple_name(
    sb: SupabaseClient,
    table: str,
    field: str,
    value: str,
    cache: Dict[str, int],
    on_created,
) -> int:
    key = value.lower()
    if key in cache:
        return cache[key]

    rows = sb.select(table, select="id", **{field: f"eq.{value}"})
    if rows:
        cache[key] = int(rows[0]["id"])
        return cache[key]

    created = sb.insert(table, [{field: value}])
    new_id = int(created[0]["id"]) if created else -1
    cache[key] = new_id
    on_created()
    return new_id


def get_or_create_size(
    sb: SupabaseClient,
    value: str,
    cache: Dict[str, int],
    stats: Stats,
) -> int:
    key = value.lower()
    if key in cache:
        return cache[key]

    rows = sb.select("sizes", select="id", value=f"eq.{value}")
    if rows:
        cache[key] = int(rows[0]["id"])
        return cache[key]

    created = sb.insert("sizes", [{"value": value}])
    new_id = int(created[0]["id"]) if created else -1
    cache[key] = new_id
    stats.sizes_created += 1
    return new_id


def get_or_create_subcategory(
    sb: SupabaseClient,
    category_id: int,
    subcat_name: str,
    cache: Dict[Tuple[int, str], int],
    stats: Stats,
) -> int:
    key = (category_id, subcat_name.lower())
    if key in cache:
        return cache[key]

    rows = sb.select(
        "subcategories",
        select="id",
        category_id=f"eq.{category_id}",
        name=f"eq.{subcat_name}",
        limit="1",
    )
    if rows:
        cache[key] = int(rows[0]["id"])
        return cache[key]

    created = sb.insert("subcategories", [{"category_id": category_id, "name": subcat_name}])
    new_id = int(created[0]["id"]) if created else -1
    cache[key] = new_id
    stats.subcategories_created += 1
    return new_id


def get_or_create_supplier(
    sb: SupabaseClient,
    supplier_name: str,
    cache: Dict[str, int],
    stats: Stats,
) -> int:
    key = supplier_name.lower()
    if key in cache:
        return cache[key]

    rows = sb.select("suppliers", select="id", name=f"eq.{supplier_name}", limit="1")
    if rows:
        cache[key] = int(rows[0]["id"])
        return cache[key]

    created = sb.insert("suppliers", [{"name": supplier_name}])
    new_id = int(created[0]["id"]) if created else -1
    cache[key] = new_id
    stats.suppliers_created += 1
    return new_id


# -----------------------------
# Model + Variant + Stock (via Supabase)
# -----------------------------
def find_or_create_model(
    sb: SupabaseClient,
    ref: Optional[str],
    nome_modelo: str,
    marca_id: int,
    categoria_id: int,
    subcategoria_id: int,
    fornecedor_id: int,
    stats: Stats,
) -> int:
    # ref null vs value: PostgREST usa "is.null"
    ref_filter = "is.null" if ref is None else f"eq.{ref}"

    rows = sb.select(
        "product_model",
        select="id",
        ref=ref_filter,
        marca_id=f"eq.{marca_id}",
        categoria_id=f"eq.{categoria_id}",
        subcategoria_id=f"eq.{subcategoria_id}",
        limit="1",
    )
    if rows:
        stats.models_reused += 1
        return int(rows[0]["id"])

    created = sb.insert("product_model", [{
        "ref": ref,
        "nome_modelo": nome_modelo,
        "marca_id": marca_id,
        "categoria_id": categoria_id,
        "subcategoria_id": subcategoria_id,
        "fornecedor_id": fornecedor_id,
        "wc_product_id": None,
    }])
    stats.models_created += 1
    return int(created[0]["id"]) if created else -1


def upsert_variant(
    sb: SupabaseClient,
    model_id: int,
    gtin: str,
    cor_id: int,
    tamanho_id: int,
    ref_keyinvoice: Optional[int],
    stats: Stats,
) -> int:
    rows = sb.upsert(
        "product_variant",
        [{
            "model_id": model_id,
            "gtin": gtin,
            "cor_id": cor_id,
            "tamanho_id": tamanho_id,
            "ref_woocomerce": None,   # conforme pediste
            "ref_keyinvoice": ref_keyinvoice,
        }],
        on_conflict="gtin",
    )
    stats.variants_upserted += 1

    # Precisa do id para stock.
    if rows:
        return int(rows[0]["id"])

    # DRY_RUN: não há retorno (e nem gravou). Tentamos buscar pelo gtin só para coerência.
    found = sb.select("product_variant", select="id", gtin=f"eq.{gtin}", limit="1")
    return int(found[0]["id"]) if found else -1


def upsert_stock_for_all_warehouses(
    sb: SupabaseClient,
    variant_id: int,
    stock_value: int,
    stats: Stats,
) -> None:
    warehouses = sb.select("warehouses", select="id")
    if not warehouses:
        raise RuntimeError("Tabela warehouses está vazia. Não dá para criar stock.")

    payload = [
        {"variant_id": variant_id, "warehouse_id": int(w["id"]), "stock": stock_value}
        for w in warehouses
    ]

    sb.upsert("warehouse_stock", payload, on_conflict="variant_id,warehouse_id")
    stats.stock_upserts += len(payload)


# -----------------------------
# ETL
# -----------------------------
def main():
    # Carrega o .env do mesmo diretório do script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(script_dir, ".env")
    load_dotenv(dotenv_path)
    logger = setup_logger()

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()

    excel_path = os.getenv("EXCEL_PATH", "").strip()
    excel_sheet = os.getenv("EXCEL_SHEET", "").strip() or None
    default_supplier = os.getenv("DEFAULT_SUPPLIER", "KeyInvoice Import").strip()
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() in {"1", "true", "yes", "y"}

    if not supabase_url or not supabase_key:
        raise SystemExit("Falta SUPABASE_URL ou SUPABASE_KEY no .env")
    if not excel_path:
        raise SystemExit("Falta EXCEL_PATH no .env")
    
    # Se o caminho do Excel não for absoluto, busca no diretório do script
    if not os.path.isabs(excel_path):
        excel_path = os.path.join(script_dir, excel_path)

    sb = SupabaseClient(supabase_url, supabase_key, dry_run=dry_run, logger=logger)
    stats = Stats()

    logger.info("Lendo Excel: %s | aba: %s", excel_path, excel_sheet or "(primeira)")
    df = pd.read_excel(excel_path, sheet_name=excel_sheet, dtype=str)
    # Limpa nomes das colunas: remove espaços extras e caracteres especiais como _x000d_
    df.columns = [str(c).strip().replace('_x000d_', '').replace('_x000D_', '') for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Faltam colunas no Excel: {missing}")

    df = df[REQUIRED_COLUMNS].rename(columns=COLMAP)

    for col in ["ref_keyinvoice", "ref_woocomerce", "categoria", "subcategoria", "marca", "nome", "cor", "tamanho"]:
        df[col] = df[col].apply(clean_str)
    df["gtin"] = df["gtin"].apply(clean_gtin)

    stats.rows_total = len(df)

    rejects_path = "etl_rejects.csv"
    with open(rejects_path, "w", newline="", encoding="utf-8") as f_rej:
        rej_writer = csv.writer(f_rej)
        rej_writer.writerow(["row_index", "reason", *df.columns.tolist()])

        # caches
        brands_cache: Dict[str, int] = {}
        categories_cache: Dict[str, int] = {}
        subcategories_cache: Dict[Tuple[int, str], int] = {}
        colors_cache: Dict[str, int] = {}
        sizes_cache: Dict[str, int] = {}
        suppliers_cache: Dict[str, int] = {}

        # fornecedor default (obrigatório no schema)
        fornecedor_id = get_or_create_supplier(sb, default_supplier, suppliers_cache, stats)

        logger.info("Iniciando ETL (Supabase REST) | dry_run=%s | supplier=%s", dry_run, default_supplier)

        for idx, row in df.iterrows():
            gtin = row["gtin"]

            # REGRA: sem GTIN, não cadastra absolutamente nada
            if not gtin:
                stats.rows_skipped_no_gtin += 1
                rej_writer.writerow([idx, "GTIN ausente (linha ignorada)", *[row.get(c) for c in df.columns]])
                continue

            stats.rows_processed += 1

            try:
                if len(gtin) < 8:
                    raise ValueError("GTIN inválido (menos de 8 dígitos)")

                categoria = row["categoria"]
                subcategoria = row["subcategoria"]
                marca = row["marca"]
                nome = row["nome"]
                cor = row["cor"]
                tamanho = row["tamanho"]

                if not all([categoria, subcategoria, marca, nome, cor, tamanho]):
                    raise ValueError("Campos obrigatórios vazios (categoria/subcategoria/marca/nome/cor/tamanho)")

                # domínios
                marca_id = get_or_create_simple_name(
                    sb, "brands", "name", marca, brands_cache,
                    lambda: setattr(stats, "brands_created", stats.brands_created + 1)
                )
                categoria_id = get_or_create_simple_name(
                    sb, "categories", "name", categoria, categories_cache,
                    lambda: setattr(stats, "categories_created", stats.categories_created + 1)
                )
                subcategoria_id = get_or_create_subcategory(sb, categoria_id, subcategoria, subcategories_cache, stats)
                cor_id = get_or_create_simple_name(
                    sb, "colors", "name", cor, colors_cache,
                    lambda: setattr(stats, "colors_created", stats.colors_created + 1)
                )
                tamanho_id = get_or_create_size(sb, tamanho, sizes_cache, stats)

                # model
                ref = row["ref_keyinvoice"]  # product_model.ref (varchar)
                model_id = find_or_create_model(
                    sb=sb,
                    ref=ref,
                    nome_modelo=nome,
                    marca_id=marca_id,
                    categoria_id=categoria_id,
                    subcategoria_id=subcategoria_id,
                    fornecedor_id=fornecedor_id,
                    stats=stats,
                )

                # variant
                ref_keyinvoice_bigint = as_int_or_none(row["ref_keyinvoice"])  # product_variant.ref_keyinvoice é bigint
                variant_id = upsert_variant(
                    sb=sb,
                    model_id=model_id,
                    gtin=gtin,
                    cor_id=cor_id,
                    tamanho_id=tamanho_id,
                    ref_keyinvoice=ref_keyinvoice_bigint,
                    stats=stats,
                )

                # stock=1 em todos os armazéns
                # (Se DRY_RUN, isto só loga)
                if variant_id != -1:
                    upsert_stock_for_all_warehouses(sb, variant_id, stock_value=1, stats=stats)

                stats.rows_ok += 1

            except Exception as e:
                stats.rows_rejected_error += 1
                rej_writer.writerow([idx, str(e), *[row.get(c) for c in df.columns]])
                logger.warning("Linha %s rejeitada por erro: %s", idx, e)

    # relatório final
    report = f"""
========================
RELATÓRIO FINAL
========================
Modo: {"DRY-RUN (sem gravar, só logs)" if dry_run else "REAL (gravando no Supabase)"}

Linhas:
- Total no Excel:                 {stats.rows_total}
- Ignoradas (sem GTIN):           {stats.rows_skipped_no_gtin}
- Processadas (com GTIN):         {stats.rows_processed}
- OK:                             {stats.rows_ok}
- Rejeitadas por erro:            {stats.rows_rejected_error}

Domínios criados:
- suppliers:      {stats.suppliers_created}
- brands:         {stats.brands_created}
- categories:     {stats.categories_created}
- subcategories:  {stats.subcategories_created}
- colors:         {stats.colors_created}
- sizes:          {stats.sizes_created}

Modelos:
- Criados:        {stats.models_created}
- Reutilizados:   {stats.models_reused}

Variantes (GTIN):
- Upserts:        {stats.variants_upserted}

Stocks:
- Upserts total:  {stats.stock_upserts}

Ficheiros:
- Log:      etl_run.log
- Rejeitos: etl_rejects.csv
========================
"""
    print(report)


if __name__ == "__main__":
    main()
