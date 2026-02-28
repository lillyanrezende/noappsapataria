"""
Script para DELETAR e depois CORRIGIR GTINs no Supabase
1. Primeiro: Identifica e deleta variantes com GTINs duplicados
2. Depois: Corrige os GTINs das variantes restantes (remove 000)
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


def buscar_variantes_para_corrigir() -> Dict[int, str]:
    """
    Busca todas as variantes com id >= 109 que terminam em 000
    Retorna {id: gtin}
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
        return {}
    
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
    
    # Criar set de todos os GTINs existentes (não corrigidos)
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
        print(f"{'ID para deletar':<20} → {'ID que mantém':<20} {'GTIN':<20}")
        print(f"{'-' * 70}")
        
        for var_id, mantem_id in list(duplicatas.items())[:20]:
            gtin = variantes_para_corrigir.get(var_id, '')
            gtin_corrigido = gtin[:-3] if gtin else ''
            print(f"{var_id:<20} → {mantem_id:<20} {gtin_corrigido:<20}")
        
        if len(duplicatas) > 20:
            print(f"... e mais {len(duplicatas) - 20} registros")
    
    return duplicatas


def deletar_variantes_duplicadas(duplicatas: Dict[int, int], dry_run: bool = True) -> int:
    """
    Deleta as variantes que têm GTINs duplicados
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
    print(f"📊 RESULTADO DAS DELEÇÕES")
    print(f"{'=' * 70}")
    print(f"✅ Deletadas: {deletados}")
    print(f"❌ Erros: {erros}")
    
    return deletados


def corrigir_gtins_restantes(variantes_para_corrigir: Dict[int, str], duplicatas_deletadas: Set[int], dry_run: bool = True) -> int:
    """
    Corrige os GTINs das variantes restantes (remove 000)
    """
    # Remover as variantes que foram deletadas
    para_corrigir = {k: v for k, v in variantes_para_corrigir.items() if k not in duplicatas_deletadas}
    
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
    1. Busca variantes
    2. Identifica duplicatas
    3. Deleta duplicatas
    4. Corrige GTINs restantes
    """
    
    print(f"\n{'=' * 70}")
    print(f"🚀 PIPELINE DE CORREÇÃO DE GTINs")
    print(f"{'=' * 70}")
    
    # Passo 1: Buscar variantes
    variantes_para_corrigir, todas_variantes = buscar_variantes_para_corrigir()
    
    if not variantes_para_corrigir:
        print(f"\n✅ Nenhuma variante para corrigir!")
        return
    
    # Passo 2: Identificar duplicatas
    duplicatas = identificar_duplicatas(variantes_para_corrigir, todas_variantes)
    
    # Passo 3: Deletar duplicatas
    deletados = deletar_variantes_duplicadas(duplicatas, dry_run=dry_run)
    
    # Passo 4: Corrigir GTINs restantes
    corrigidos = corrigir_gtins_restantes(variantes_para_corrigir, set(duplicatas.keys()), dry_run=dry_run)
    
    # Resumo final
    print(f"\n{'=' * 70}")
    print(f"📊 RESUMO FINAL DO PIPELINE")
    print(f"{'=' * 70}")
    print(f"✅ Variantes deletadas: {deletados}")
    print(f"✅ GTINs corrigidos: {corrigidos}")
    print(f"✅ Total processado: {deletados + corrigidos}")
    
    if dry_run:
        print(f"\n💡 Para executar de verdade, use: python {sys.argv[0]} --real")


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
