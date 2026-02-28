"""
Script para corrigir GTINs no Supabase - Remove os últimos '000' dos GTINs
A partir da variante_id 109
"""

import os
from dotenv import load_dotenv
import requests
from typing import List, Dict

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


def listar_gtins_para_corrigir(dry_run: bool = True) -> List[Dict]:
    """
    Lista todos os GTINs que serão corrigidos (terminam com 000)
    """
    print(f"\n{'=' * 70}")
    print(f"🔍 LISTANDO GTINs PARA CORREÇÃO (id >= 109)")
    print(f"{'=' * 70}")
    
    # Buscar variantes com id >= 109
    url = f"{SUPABASE_URL}/rest/v1/product_variant"
    params = {
        "id": "gte.109",
        "select": "id,gtin,model_id",
        "order": "id.asc"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"❌ Erro ao buscar variantes: {response.status_code}")
        print(response.text)
        return []
    
    variantes = response.json()
    print(f"📊 Total de variantes encontradas (id >= 109): {len(variantes)}")
    
    # Filtrar apenas as que terminam com '000' e têm mais de 11 caracteres
    para_corrigir = []
    
    for var in variantes:
        gtin = var.get('gtin', '')
        if gtin and len(gtin) > 11 and gtin.endswith('000') and gtin.isdigit():
            gtin_corrigido = gtin[:-3]  # Remove últimos 3 caracteres
            para_corrigir.append({
                'id': var['id'],
                'gtin_atual': gtin,
                'gtin_corrigido': gtin_corrigido,
                'model_id': var.get('model_id')
            })
    
    print(f"✅ GTINs que precisam correção: {len(para_corrigir)}")
    print(f"\n📋 PRIMEIRAS 10 CORREÇÕES:")
    print(f"{'-' * 70}")
    print(f"{'ID':<8} {'GTIN Atual':<20} → {'GTIN Corrigido':<20}")
    print(f"{'-' * 70}")
    
    for item in para_corrigir[:10]:
        print(f"{item['id']:<8} {item['gtin_atual']:<20} → {item['gtin_corrigido']:<20}")
    
    if len(para_corrigir) > 10:
        print(f"... e mais {len(para_corrigir) - 10} registros")
    
    return para_corrigir


def corrigir_gtins(dry_run: bool = True) -> None:
    """
    Executa a correção dos GTINs no banco de dados
    """
    para_corrigir = listar_gtins_para_corrigir(dry_run)
    
    if not para_corrigir:
        print("\n✅ Nenhum GTIN precisa ser corrigido!")
        return
    
    print(f"\n{'=' * 70}")
    if dry_run:
        print(f"🧪 MODO DRY RUN - Nenhuma alteração será feita no banco")
    else:
        print(f"⚠️  MODO REAL - As alterações serão aplicadas no banco de dados!")
    print(f"{'=' * 70}")
    
    if not dry_run:
        confirmacao = input(f"\n⚠️  Deseja REALMENTE corrigir {len(para_corrigir)} GTINs? (digite 'SIM' para confirmar): ")
        if confirmacao.upper() != 'SIM':
            print("❌ Operação cancelada pelo usuário.")
            return
    
    sucesso = 0
    erros = 0
    
    url = f"{SUPABASE_URL}/rest/v1/product_variant"
    
    for item in para_corrigir:
        variant_id = item['id']
        gtin_corrigido = item['gtin_corrigido']
        
        if dry_run:
            print(f"   [DRY RUN] Variante {variant_id}: {item['gtin_atual']} → {gtin_corrigido}")
            sucesso += 1
        else:
            # Executar a atualização real
            try:
                update_url = f"{url}?id=eq.{variant_id}"
                payload = {"gtin": gtin_corrigido}
                
                response = requests.patch(update_url, headers=headers, json=payload)
                
                if response.status_code in [200, 204]:
                    print(f"   ✅ Variante {variant_id}: {item['gtin_atual']} → {gtin_corrigido}")
                    sucesso += 1
                else:
                    print(f"   ❌ Erro variante {variant_id}: {response.status_code} - {response.text}")
                    erros += 1
                    
            except Exception as e:
                print(f"   ❌ Exceção variante {variant_id}: {e}")
                erros += 1
    
    print(f"\n{'=' * 70}")
    print(f"📊 RESULTADO DA CORREÇÃO")
    print(f"{'=' * 70}")
    print(f"✅ Sucesso: {sucesso}")
    print(f"❌ Erros: {erros}")
    print(f"📝 Total processado: {len(para_corrigir)}")
    
    if dry_run:
        print(f"\n💡 Para aplicar as alterações, execute:")
        print(f"   python corrigir_gtins.py --real")


if __name__ == "__main__":
    import sys
    
    # Verificar argumentos da linha de comando
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] in ['--real', '--execute', '--apply']:
        dry_run = False
    
    try:
        corrigir_gtins(dry_run=dry_run)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
