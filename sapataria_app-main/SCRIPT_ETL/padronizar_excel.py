"""
Script para padronizar dados do Excel antes de importar
- Remove espaços extras
- Padroniza capitalização (marcas, categorias, etc.)
- Remove caracteres especiais de colunas
- Limpa GTINs
"""
import os
import pandas as pd
from datetime import datetime

# Caminhos
script_dir = os.path.dirname(os.path.abspath(__file__))
excel_path = os.path.join(script_dir, "Online Codigos de Barras.xlsx")
backup_path = os.path.join(script_dir, f"Online Codigos de Barras_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

print(f"📂 Lendo Excel: {excel_path}")
df = pd.read_excel(excel_path, sheet_name="Folha1", dtype=str)

# Limpar nomes das colunas
print("🔧 Limpando nomes das colunas...")
df.columns = [str(c).strip().replace('_x000d_', '').replace('_x000D_', '') for c in df.columns]

# Backup antes de modificar
print(f"💾 Criando backup: {backup_path}")
df.to_excel(backup_path, sheet_name="Folha1", index=False)

# Estatísticas antes
print("\n📊 ANTES da padronização:")
print(f"  - Total de linhas: {len(df)}")
if 'Marca' in df.columns:
    print(f"  - Marcas únicas: {df['Marca'].nunique()}")
    print(f"    {df['Marca'].value_counts().head(10).to_dict()}")

# Função para limpar strings
def clean_text(x):
    if pd.isna(x) or x is None:
        return x
    s = str(x).strip()
    if s.lower() in ['nan', 'none', 'null', '']:
        return None
    return s

# Função para padronizar capitalização (primeira letra maiúscula)
def capitalize_text(x):
    x = clean_text(x)
    if x is None or pd.isna(x):
        return x
    x = str(x).strip()
    # Casos especiais - manter maiúsculas
    if x.upper() in ['SORRISO', 'BIANCA', 'HÉLIA']:
        return x.upper()
    return x.title()

# Função para limpar GTIN
def clean_gtin(x):
    x = clean_text(x)
    if x is None:
        return x
    # Remove espaços, hífens
    s = x.replace(" ", "").replace("-", "")
    # Mantém apenas dígitos
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits if digits else None

print("\n🔧 Padronizando dados...")

# Padronizar campos de texto
text_fields = ['Ref. Keyinvoice', 'Ref. Woocomerce', 'Categoria', 'Subcategoria', 
               'Marca', 'Nome', 'Cor', 'TAMANHO']

for field in text_fields:
    if field in df.columns:
        print(f"  ✓ Limpando: {field}")
        df[field] = df[field].apply(clean_text)
        
        # Padronizar capitalização para certos campos
        if field in ['Marca', 'Categoria', 'Subcategoria', 'Cor']:
            df[field] = df[field].apply(capitalize_text)

# Limpar GTIN
if 'CODIGO DE BARRAS' in df.columns:
    print(f"  ✓ Limpando: CODIGO DE BARRAS (GTIN)")
    df['CODIGO DE BARRAS'] = df['CODIGO DE BARRAS'].apply(clean_gtin)

# Estatísticas depois
print("\n📊 DEPOIS da padronização:")
print(f"  - Total de linhas: {len(df)}")
if 'Marca' in df.columns:
    print(f"  - Marcas únicas: {df['Marca'].nunique()}")
    print(f"    {df['Marca'].value_counts().head(10).to_dict()}")

if 'CODIGO DE BARRAS' in df.columns:
    gtins_validos = df['CODIGO DE BARRAS'].notna() & (df['CODIGO DE BARRAS'].str.len() >= 8)
    print(f"  - GTINs válidos (≥8 dígitos): {gtins_validos.sum()}")
    print(f"  - GTINs inválidos: {len(df) - gtins_validos.sum()}")

# Salvar Excel padronizado
print(f"\n💾 Salvando Excel padronizado...")
df.to_excel(excel_path, sheet_name="Folha1", index=False)

print(f"\n✅ Concluído!")
print(f"  - Original (backup): {backup_path}")
print(f"  - Padronizado: {excel_path}")
