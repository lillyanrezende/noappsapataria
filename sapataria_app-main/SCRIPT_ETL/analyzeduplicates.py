import pandas as pd
from collections import Counter

# Ler o arquivo Excel
df = pd.read_excel('CDB NOVOS PARA ETL.xlsx', sheet_name='Folha1', dtype=str)

# Limpar nomes das colunas
df.columns = [str(c).strip().replace('_x000d_', '').replace('_x000D_', '') for c in df.columns]

print("=" * 80)
print("ANÁLISE DE CÓDIGOS INTERNOS (GTIN) DUPLICADOS")
print("=" * 80)
print()

# Limpar e processar GTINs
def clean_gtin(x):
    if x is None or pd.isna(x):
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return None
    # Remove espaços e hífens, mantém apenas dígitos
    s = s.replace(" ", "").replace("-", "")
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits if digits else None

# Aplicar limpeza
df['gtin_limpo'] = df['CODIGOS INTERNOS'].apply(clean_gtin)

# Remover linhas sem GTIN
df_com_gtin = df[df['gtin_limpo'].notna()].copy()

print(f"Total de linhas no Excel: {len(df)}")
print(f"Linhas com GTIN válido: {len(df_com_gtin)}")
print()

# Contar frequências
gtin_counts = Counter(df_com_gtin['gtin_limpo'].values)

# Encontrar duplicados
duplicados = {gtin: count for gtin, count in gtin_counts.items() if count > 1}

print(f"Total de GTINs únicos: {len(gtin_counts)}")
print(f"Total de GTINs com repetição: {len(duplicados)}")
print()

if duplicados:
    print("=" * 80)
    print("CÓDIGOS REPETIDOS NA PLANILHA:")
    print("=" * 80)
    print()
    
    # Ordenar por frequência (mais repetidos primeiro)
    duplicados_sorted = sorted(duplicados.items(), key=lambda x: x[1], reverse=True)
    
    total_linhas_duplicadas = 0
    for i, (gtin, count) in enumerate(duplicados_sorted, 1):
        print(f"{i}. GTIN: {gtin} - Repetido {count} vezes")
        
        # Mostrar a qual linha cada ocorrência apareça
        linhas = df_com_gtin[df_com_gtin['gtin_limpo'] == gtin].index.tolist()
        print(f"   Linhas: {', '.join([str(l+2) for l in linhas])}")  # +2 porque é 1-based e tem header
        
        # Mostrar produtos associados
        produtos = df_com_gtin[df_com_gtin['gtin_limpo'] == gtin][['Ref. Keyinvoice', 'Nome', 'Cor', 'TAMANHO']].drop_duplicates()
        for idx, row in produtos.iterrows():
            print(f"      - {row['Nome']} | Cor: {row['Cor']} | Tamanho: {row['TAMANHO']}")
        
        print()
        total_linhas_duplicadas += (count - 1)  # Conta quantas linhas são "extras"
    
    print("=" * 80)
    print(f"Resumo: {len(duplicados)} GTINs duplicados")
    print(f"Total de linhas que seriam rejeitadas: {total_linhas_duplicadas}")
    print("=" * 80)
else:
    print("✅ Nenhum GTIN repetido encontrado na planilha!")
