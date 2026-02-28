"""
Script para DELETAR e CORRIGIR GTINs no Supabase
COM TRATAMENTO DE CONSTRAINTS DE CHAVE ESTRANGEIRA

Ordem correta:
1. Deletar warehouse_stock que referenciam variantes com GTIN duplicado
2. Deletar product_variant com GTIN duplicado
3. Corrigir GTINs das variantes restantes
"""

import os
from dotenv import load_dotenv
import requests
from typing import List, Dict, Set
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


def buscar_variantes_para_corrigir() -> tuple:
    """
    Busca todas as variantes com id >= 109 que terminam em 000
    Retorna (variantes_para_corrigir, todas_variantes)
    """
    print(f"\n{'=' * 70}")
    print(f"🔍 BUSCANDO VARIANTES PARA CORRIGIR (id >= 109)")
    print(f"{'=' * 70}")
    
    url = f"{SUPABASE_URL}/rest/v1/product_variant"
    params = {
        "id": "gte.109",
        "select": "id,gtin",
        "order": "id.asc"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"❌ Erro ao buscar variantes: {response.status_code}")
        print(response.text)
        return {}, []
    
    variantes = response.json()
    print(f"📊 Total de variantes encontradas (id >= 109): {len(variantes)}")
    
    # Filtrar apenas as que terminam com '000' e são válidas
    variantes_para_corrigir = {}
    
    for var in variantes:
        gtin = var.get('gtin', '')
        if gtin and len(gtin) > 11 and gtin.endswith('000') and gtin.isdigit():
            variantes_para_corrigir[var['id']] = gtin
    
    print(f"✅ Variantes que precisam correção: {len(variantes_para_corrigir)}")
    
    return variantes_para_corrigir, variantes


def identificar_duplicatas(variantes_para_corrigir: Dict[int, str], todas_variantes: List[Dict]) -> Dict[int, int]:
    """
    Identifica variantes que, após remover 000, terão GTIN duplicado
    Retorna {id_para_deletar: id_que_mantem}
    """
    print(f"\n{'=' * 70}")
    print(f"🔍 IDENTIFICANDO GTINs DUPLICADOS")
    print(f"{'=' * 70}")
    
    # Criar dict de todos os GTINs existentes
    gtins_existentes = {v['id']: v.get('gtin', '') for v in todas_variantes}
    
    duplicatas = {}  # {id_para_deletar: id_que_mantem}
    
    for var_id, gtin_com_000 in variantes_para_corrigir.items():
        gtin_corrigido = gtin_com_000[:-3]  # Remove últimos 3 caracteres
        
        # Procurar se já existe um GTIN com esse valor (sem os 000)
        for outra_id, outro_gtin in gtins_existentes.items():
            if outro_gtin == gtin_corrigido and outra_id != var_id:
                duplicatas[var_id] = outra_id
                break
    
    print(f"⚠️  Total de variantes com GTINs duplicados: {len(duplicatas)}")
    
    if duplicatas:
        print(f"\n📋 VARIANTES QUE SERÃO DELETADAS (por terem GTIN duplicado):")
        print(f"{'-' * 70}")
        print(f"{'ID DEL':<15} → {'ID MANTEM':<15} {'GTIN CORRIGIDO':<20}")
        print(f"{'-' * 70}")
        
        for var_id, mantem_id in list(duplicatas.items())[:20]:
            gtin = variantes_para_corrigir.get(var_id, '')
            gtin_corrigido = gtin[:-3] if gtin else ''
            print(f"{var_id:<15} → {mantem_id:<15} {gtin_corrigido:<20}")
        
        if len(duplicatas) > 20:
            print(f"... e mais {len(duplicatas) - 20} registros")
    
    return duplicatas


def buscar_warehouse_stock_para_deletar(variantes_duplicadas: Set[int]) -> List[Dict]:
    """
    Busca registros de warehouse_stock que referenciam as variantes a deletar
    """
    print(f"\n{'=' * 70}")
    print(f"🔍 PROCURANDO warehouse_stock PARA DELETAR")
    print(f"{'=' * 70}")
    
    # Construir query para buscar warehouse_stock
    url = f"{SUPABASE_URL}/rest/v1/warehouse_stock"
    
    # Supabase não suporta IN nativo no REST, então fazemos múltiplas requisições
    registros_ws = []
    
    # Buscar em chunks de 100 variantes
    chunk_size = 100
    var_list = list(variantes_duplicadas)
    
    for i in range(0, len(var_list), chunk_size):
        chunk = var_list[i:i+chunk_size]
        
        # Criar OR filter para variant_id
        filters = []
        for var_id in chunk:
            filters.append(f"variant_id.eq.{var_id}")
        
        filter_str = ",".join(filters)
        
        params = {
            "select": "id,variant_id,quantity",
            "or": f"({filter_str})"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                registros_ws.extend(response.json())
        except:
            pass
    
    # Se não conseguiu com OR, tenta de outro jeito
    if not registros_ws:
        for var_id in variantes_duplicadas:
            params = {"variant_id": f"eq.{var_id}"}
            try:
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    registros_ws.extend(response.json())
            except:
                pass
    
    print(f"📦 Registros warehouse_stock encontrados: {len(registros_ws)}")
    
    if registros_ws:
        print(f"\n📋 PRIMEIROS 10 warehouse_stock A DELETAR:")
        print(f"{'-' * 70}")
        for ws in registros_ws[:10]:
            print(f"   warehouse_stock.id={ws['id']} → variante {ws['variant_id']} (qtd: {ws.get('quantity', 0)})")
        
        if len(registros_ws) > 10:
            print(f"   ... e mais {len(registros_ws) - 10} registros")
    
    return registros_ws


def deletar_warehouse_stock(registros_ws: List[Dict], dry_run: bool = True) -> int:
    """
    Deleta registros de warehouse_stock
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
        confirmacao = input(f"\n⚠️  ATENÇÃO! Deseja DELETAR {len(registros_ws)} warehouse_stock? (digite 'DELETAR' para confirmar): ")
        if confirmacao.upper() != 'DELETAR':
            print("❌ Operação cancelada pelo usuário.")
            return 0
    
    url = f"{SUPABASE_URL}/rest/v1/warehouse_stock"
    deletados = 0
    erros = 0
    
    for ws in registros_ws:
        ws_id = ws['id']
        
        if dry_run:
            print(f"   [DRY RUN] Deletaria warehouse_stock {ws_id}")
            deletados += 1
        else:
            try:
                delete_url = f"{url}?id=eq.{ws_id}"
                response = requests.delete(delete_url, headers=headers)
                
                if response.status_code in [200, 204, 206]:
                    print(f"   ✅ Deletado warehouse_stock {ws_id}")
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


def deletar_variantes_duplicadas(duplicatas: Dict[int, int], dry_run: bool = True) -> int:
    """
    Deleta as variantes que têm GTINs duplicados
    (Deve ser executado APÓS deletar warehouse_stock)
    """
    if not duplicatas:
        print(f"\n✅ Nenhuma variante com GTIN duplicado para deletar!")
        return 0
    
    print(f"\n{'=' * 70}")
    if dry_run:
        print(f"🧪 MODO DRY RUN - Nenhuma deleção será feita")
    else:
        print(f"⚠️  MODO REAL - VARIANTES SERÃO DELETADAS!")
    print(f"{'=' * 70}")
    
    if not dry_run:
        confirmacao = input(f"\n⚠️  ATENÇÃO! Deseja DELETAR {len(duplicatas)} variantes? (digite 'DELETAR' para confirmar): ")
        if confirmacao.upper() != 'DELETAR':
            print("❌ Operação cancelada pelo usuário.")
            return 0
    
    url = f"{SUPABASE_URL}/rest/v1/product_variant"
    deletados = 0
    erros = 0
    
    for var_id in duplicatas.keys():
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
    print(f"📊 RESULTADO DAS DELEÇÕES (variantes)")
    print(f"{'=' * 70}")
    print(f"✅ Deletadas: {deletados}")
    print(f"❌ Erros: {erros}")
    
    return deletados


def corrigir_gtins_restantes(variantes_para_corrigir: Dict[int, str], variantes_deletadas: Set[int], dry_run: bool = True) -> int:
    """
    Corrige os GTINs das variantes restantes (remove 000)
    """
    # Remover as variantes que foram deletadas
    para_corrigir = {k: v for k, v in variantes_para_corrigir.items() if k not in variantes_deletadas}
    
    print(f"\n{'=' * 70}")
    print(f"✏️  CORRIGINDO GTINs DAS VARIANTES RESTANTES")
    print(f"{'=' * 70}")
    print(f"Total a corrigir: {len(para_corrigir)}")
    
    if not para_corrigir:
        print(f"✅ Nenhuma variante para corrigir!")
        return 0
    
    if dry_run:
        print(f"🧪 MODO DRY RUN - Nenhuma alteração será feita")
    else:
        print(f"⚠️  MODO REAL - GTINs SERÃO CORRIGIDOS!")
    
    print(f"{'=' * 70}")
    
    if not dry_run:
        confirmacao = input(f"\n⚠️  Deseja REALMENTE corrigir {len(para_corrigir)} GTINs? (digite 'SIM' para confirmar): ")
        if confirmacao.upper() != 'SIM':
            print("❌ Operação cancelada pelo usuário.")
            return 0
    
    url = f"{SUPABASE_URL}/rest/v1/product_variant"
    corrigidos = 0
    erros = 0
    
    for var_id, gtin_com_000 in para_corrigir.items():
        gtin_corrigido = gtin_com_000[:-3]
        
        if dry_run:
            print(f"   [DRY RUN] Variante {var_id}: {gtin_com_000} → {gtin_corrigido}")
            corrigidos += 1
        else:
            try:
                update_url = f"{url}?id=eq.{var_id}"
                payload = {"gtin": gtin_corrigido}
                
                response = requests.patch(update_url, headers=headers, json=payload)
                
                if response.status_code in [200, 204]:
                    print(f"   ✅ Corrigida variante {var_id}: {gtin_corrigido}")
                    corrigidos += 1
                else:
                    print(f"   ❌ Erro variante {var_id}: {response.status_code}")
                    erros += 1
                    
            except Exception as e:
                print(f"   ❌ Exceção variante {var_id}: {e}")
                erros += 1
    
    print(f"\n{'=' * 70}")
    print(f"📊 RESULTADO DA CORREÇÃO")
    print(f"{'=' * 70}")
    print(f"✅ Corrigidas: {corrigidos}")
    print(f"❌ Erros: {erros}")
    
    return corrigidos


def main(dry_run: bool = True):
    """
    Executa o pipeline completo:
    1. Busca variantes com GTIN terminado em 000
    2. Identifica variantes com GTIN duplicado
    3. Busca e deleta warehouse_stock relacionado
    4. Deleta variantes duplicadas
    5. Corrige GTINs das variantes restantes
    """
    
    print(f"\n{'=' * 70}")
    print(f"🚀 PIPELINE DE CORREÇÃO DE GTINs COM FK HANDLING")
    print(f"{'=' * 70}")
    
    # Passo 1: Buscar variantes
    variantes_para_corrigir, todas_variantes = buscar_variantes_para_corrigir()
    
    if not variantes_para_corrigir:
        print(f"\n✅ Nenhuma variante para corrigir!")
        return
    
    # Passo 2: Identificar duplicatas
    duplicatas = identificar_duplicatas(variantes_para_corrigir, todas_variantes)
    
    # Passo 3: Buscar warehouse_stock
    registros_ws = buscar_warehouse_stock_para_deletar(set(duplicatas.keys()))
    
    # Passo 4: Deletar warehouse_stock (PRIMEIRO!)
    deletados_ws = deletar_warehouse_stock(registros_ws, dry_run=dry_run)
    
    # Passo 5: Deletar variantes
    deletados_var = deletar_variantes_duplicadas(duplicatas, dry_run=dry_run)
    
    # Passo 6: Corrigir GTINs restantes
    corrigidos = corrigir_gtins_restantes(variantes_para_corrigir, set(duplicatas.keys()), dry_run=dry_run)
    
    # Resumo final
    print(f"\n{'=' * 70}")
    print(f"📊 RESUMO FINAL DO PIPELINE")
    print(f"{'=' * 70}")
    print(f"✅ warehouse_stock deletados: {deletados_ws}")
    print(f"✅ Variantes deletadas: {deletados_var}")
    print(f"✅ GTINs corrigidos: {corrigidos}")
    print(f"✅ Total processado: {deletados_ws + deletados_var + corrigidos}")
    
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
