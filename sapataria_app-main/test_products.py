from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("ERRO: Variáveis SUPABASE_URL ou SUPABASE_KEY não encontradas no .env")
    exit(1)

supabase = create_client(url, key)

print("Testando busca de produtos...")

# Testar busca específica
gtin_teste = "15600921603384"  # Usar o GTIN que vimos na listagem
print(f"\nTestando busca do GTIN: {gtin_teste}")

try:
    # Teste do método find_variant_by_gtin
    response = supabase.table('product_variant').select('*, product_model(*)').eq('gtin', gtin_teste).execute()
    if response.data:
        row = response.data[0]
        model = row['product_model']
        result = {
            'variant_id': row['id'],
            'gtin': row['gtin'],
            'model_id': row['model_id'],
            'cor_id': row['cor_id'],
            'tamanho_id': row['tamanho_id'],
            'ref_keyinvoice': row['ref_keyinvoice'],
            'nome_modelo': model['nome_modelo'],
            'marca_id': model['marca_id'],
            'categoria_id': model['categoria_id'],
            'subcategoria_id': model['subcategoria_id'],
            'fornecedor_id': model['fornecedor_id']
        }
        print("✅ Produto encontrado (find_variant_by_gtin):")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print("❌ GTIN não encontrado")

    # Teste do método get_full_view_by_gtin
    print(f"\nTestando visualização completa do GTIN: {gtin_teste}")
    response2 = supabase.table('product_variant').select('*, product_model(*, brands(*), categories(*), subcategories(*), suppliers(*)), colors(*), sizes(*)').eq('gtin', gtin_teste).execute()
    if response2.data:
        row = response2.data[0]
        header = {
            'variant_id': row['id'],
            'gtin': row['gtin'],
            'ref_keyinvoice': row['ref_keyinvoice'],
            'nome_modelo': row['product_model']['nome_modelo'],
            'marca': row['product_model']['brands']['name'],
            'categoria': row['product_model']['categories']['name'],
            'subcategoria': row['product_model']['subcategories']['name'],
            'fornecedor': row['product_model']['suppliers']['name'],
            'cor': row['colors']['name'],
            'tamanho': row['sizes']['value']
        }
        print("✅ Visualização completa:")
        for key, value in header.items():
            print(f"  {key}: {value}")

        # Verificar stocks
        stocks_response = supabase.table('warehouse_stock').select('stock, warehouses(name)').eq('variant_id', row['id']).execute()
        stocks = [{'armazem': s['warehouses']['name'], 'stock': s['stock']} for s in stocks_response.data]
        print("  Stocks:")
        for stock in stocks:
            print(f"    {stock['armazem']}: {stock['stock']}")
    else:
        print("❌ GTIN não encontrado na visualização completa")

except Exception as e:
    print(f"Erro durante teste: {e}")
    import traceback
    traceback.print_exc()

print("\nTeste concluído!")