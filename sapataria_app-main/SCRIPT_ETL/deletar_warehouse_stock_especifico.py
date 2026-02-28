"""
Script para deletar warehouse_stock e product_variant específicos
Variantes com GTIN duplicado já identificadas
"""

import os
from dotenv import load_dotenv
import requests
import sys

load_dotenv()

# Configuração Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas no .env")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# IDs das variantes a deletar (com GTIN duplicado)
VARIANTES_DUPLICADAS = [
    488, 489, 490, 491, 492, 495, 496, 501, 504, 505,
    506, 507, 509, 510, 511, 512, 513, 514, 515, 516, 517
]


def buscar_warehouse_stock_para_deletar(dry_run: bool = True) -> list:
    """
    Busca registros de warehouse_stock que referenciam as variantes duplicadas
    """
    print(f"\n{'=' * 70}")
    print(f"🔍 BUSCANDO warehouse_stock PARA DELETAR")
    print(f"{'=' * 70}")
    print(f"Variantes a processar: {len(VARIANTES_DUPLICADAS)}")
    print(f"IDs: {VARIANTES_DUPLICADAS}")
    
    registros_ws = []
    url = f"{SUPABASE_URL}/rest/v1/warehouse_stock"
    
    # Buscar warehouse_stock para cada variante
    for var_id in VARIANTES_DUPLICADAS:
        params = {"variant_id": f"eq.{var_id}"}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                records = response.json()
                registros_ws.extend(records)
                if records:
                    print(f"   Variante {var_id}: {len(records)} warehouse_stock encontrado(s)")
        except Exception as e:
            print(f"   ❌ Erro ao buscar variante {var_id}: {e}")
    
    print(f"\n📦 Total de warehouse_stock encontrado: {len(registros_ws)}")
    
    if registros_ws:
        print(f"\n📋 PRIMEIROS 20 warehouse_stock A DELETAR:")
        print(f"{'-' * 70}")
        print(f"{'ID':<10} {'Variante':<15} {'Warehouse':<15} {'Quantidade':<10}")
        print(f"{'-' * 70}")
        
        for ws in registros_ws[:20]:
            print(f"{ws['id']:<10} {ws['variant_id']:<15} {ws.get('warehouse_id', 'N/A'):<15} {ws.get('quantity', 0):<10}")
        
        if len(registros_ws) > 20:
            print(f"... e mais {len(registros_ws) - 20} registros")
    
    return registros_ws


def deletar_warehouse_stock(registros_ws: list, dry_run: bool = True) -> int:
    """
    Deleta os registros de warehouse_stock
    """
    if not registros_ws:
        print(f"\n✅ Nenhum warehouse_stock para deletar!")
        return 0
    
    print(f"\n{'=' * 70}")
    if dry_run:
        print(f"🧪 MODO DRY RUN - Nenhuma deleção será feita")
    else:
        print(f"⚠️  MODO REAL - warehouse_stock SERÁ DELETADO!")
    print(f"{'=' * 70}")
    
    if not dry_run:
        print(f"\n📊 RESUMO DA OPERAÇÃO:")
        print(f"   • Total de warehouse_stock a deletar: {len(registros_ws)}")
        confirmacao = input(f"\n⚠️  ATENÇÃO! Deseja DELETAR {len(registros_ws)} warehouse_stock? (digite 'DELETAR' para confirmar): ")
        if confirmacao.upper() != 'DELETAR':
            print("❌ Operação cancelada pelo usuário.")
            return 0
    
    url = f"{SUPABASE_URL}/rest/v1/warehouse_stock"
    deletados = 0
    erros = 0
    
    for ws in registros_ws:
        ws_id = ws['id']
        var_id = ws['variant_id']
        
        if dry_run:
            print(f"   [DRY RUN] Deletaria warehouse_stock {ws_id} (variante {var_id})")
            deletados += 1
        else:
            try:
                delete_url = f"{url}?id=eq.{ws_id}"
                response = requests.delete(delete_url, headers=headers)
                
                if response.status_code in [200, 204, 206]:
                    print(f"   ✅ Deletado warehouse_stock {ws_id} (variante {var_id})")
                    deletados += 1
                else:
                    print(f"   ❌ Erro ao deletar warehouse_stock {ws_id}: {response.status_code}")
                    erros += 1
                    
            except Exception as e:
                print(f"   ❌ Exceção warehouse_stock {ws_id}: {e}")
                erros += 1
    
    print(f"\n{'=' * 70}")
    print(f"📊 RESULTADO DAS DELEÇÕES (warehouse_stock)")
    print(f"{'=' * 70}")
    print(f"✅ Deletados: {deletados}")
    print(f"❌ Erros: {erros}")
    
    return deletados


def deletar_variantes_duplicadas(dry_run: bool = True) -> int:
    """
    Deleta as variantes duplicadas
    (Deve ser executado APÓS deletar warehouse_stock)
    """
    print(f"\n{'=' * 70}")
    print(f"🗑️  DELETANDO product_variant")
    print(f"{'=' * 70}")
    
    if dry_run:
        print(f"🧪 MODO DRY RUN - Nenhuma deleção será feita")
    else:
        print(f"⚠️  MODO REAL - VARIANTES SERÁ DELETADA!")
    
    print(f"{'=' * 70}")
    print(f"Total de variantes a deletar: {len(VARIANTES_DUPLICADAS)}")
    
    if not dry_run:
        confirmacao = input(f"\n⚠️  ATENÇÃO! Deseja DELETAR {len(VARIANTES_DUPLICADAS)} variantes? (digite 'DELETAR' para confirmar): ")
        if confirmacao.upper() != 'DELETAR':
            print("❌ Operação cancelada pelo usuário.")
            return 0
    
    url = f"{SUPABASE_URL}/rest/v1/product_variant"
    deletados = 0
    erros = 0
    
    for var_id in VARIANTES_DUPLICADAS:
        if dry_run:
            print(f"   [DRY RUN] Deletaria variante {var_id}")
            deletados += 1
        else:
            try:
                delete_url = f"{url}?id=eq.{var_id}"
                response = requests.delete(delete_url, headers=headers)
                
                if response.status_code in [200, 204, 206]:
                    print(f"   ✅ Deletada variante {var_id}")
                    deletados += 1
                else:
                    print(f"   ❌ Erro ao deletar {var_id}: {response.status_code}")
                    erros += 1
                    
            except Exception as e:
                print(f"   ❌ Exceção {var_id}: {e}")
                erros += 1
    
    print(f"\n{'=' * 70}")
    print(f"📊 RESULTADO DAS DELEÇÕES (product_variant)")
    print(f"{'=' * 70}")
    print(f"✅ Deletadas: {deletados}")
    print(f"❌ Erros: {erros}")
    
    return deletados


def main(dry_run: bool = True):
    """
    Executa o pipeline:
    1. Busca warehouse_stock
    2. Deleta warehouse_stock
    3. Deleta product_variant
    """
    
    print(f"\n{'=' * 70}")
    print(f"🚀 DELETAR warehouse_stock E product_variant ESPECÍFICOS")
    print(f"{'=' * 70}")
    
    # Passo 1: Buscar warehouse_stock
    registros_ws = buscar_warehouse_stock_para_deletar(dry_run=dry_run)
    
    # Passo 2: Deletar warehouse_stock
    deletados_ws = deletar_warehouse_stock(registros_ws, dry_run=dry_run)
    
    # Passo 3: Deletar variantes
    deletados_var = deletar_variantes_duplicadas(dry_run=dry_run)
    
    # Resumo final
    print(f"\n{'=' * 70}")
    print(f"📊 RESUMO FINAL")
    print(f"{'=' * 70}")
    print(f"✅ warehouse_stock deletados: {deletados_ws}")
    print(f"✅ Variantes deletadas: {deletados_var}")
    print(f"✅ Total processado: {deletados_ws + deletados_var}")
    
    if dry_run:
        print(f"\n💡 Para executar de verdade, use:")
        print(f"   python {sys.argv[0]} --real")


if __name__ == "__main__":
    dry_run = True
    
    if len(sys.argv) > 1 and sys.argv[1] in ['--real', '--execute', '--apply']:
        dry_run = False
    
    try:
        main(dry_run=dry_run)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
