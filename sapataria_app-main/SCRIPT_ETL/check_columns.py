import pandas as pd

df = pd.read_excel('CDB NOVOS PARA ETL.xlsx')
print("Número de linhas:", len(df))
print("\nColunas encontradas:")
for i, col in enumerate(df.columns):
    print(f"  {i+1}. {col}")
