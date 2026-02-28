"""
Script para gerar relatório Excel dos produtos processados com SUCESSO no ETL.
Remove as linhas rejeitadas e salva apenas as que deram certo.
"""

import pandas as pd
from datetime import datetime
import os

def gerar_relatorio_sucesso():
    """
    Lê o Excel original e o CSV de rejeições,
    e cria um novo Excel apenas com os produtos que foram processados com sucesso.
    """
    
    # Caminhos dos arquivos
    excel_original = "Online Codigos de Barras.xlsx"
    rejects_csv = "etl_rejects.csv"
    
    # Verificar se os arquivos existem
    if not os.path.exists(excel_original):
        print(f"❌ Erro: Arquivo '{excel_original}' não encontrado!")
        return
    
    if not os.path.exists(rejects_csv):
        print(f"❌ Erro: Arquivo '{rejects_csv}' não encontrado!")
        return
    
    print(f"📖 Lendo arquivo: {excel_original}")
    df_original = pd.read_excel(excel_original, sheet_name="Folha1")
    total_original = len(df_original)
    print(f"   Total de linhas no Excel original: {total_original}")
    
    print(f"\n📖 Lendo arquivo de rejeições: {rejects_csv}")
    df_rejects = pd.read_csv(rejects_csv)
    total_rejeitadas = len(df_rejects)
    print(f"   Total de linhas rejeitadas: {total_rejeitadas}")
    
    # Obter índices das linhas rejeitadas (row_index é 1-based no CSV)
    # Converter para 0-based para usar com pandas
    indices_rejeitados = set(df_rejects['row_index'].tolist())
    
    # Criar lista de índices com base 1 (como no arquivo)
    # DataFrame pandas usa índice 0-based, mas o row_index no CSV é 1-based
    # então a linha 1 do CSV corresponde ao índice 0 do DataFrame
    indices_rejeitados_0based = {idx - 1 for idx in indices_rejeitados}
    
    print(f"\n🔍 Filtrando produtos processados com sucesso...")
    # Manter apenas as linhas que NÃO estão na lista de rejeitados
    df_sucesso = df_original[~df_original.index.isin(indices_rejeitados_0based)].copy()
    total_sucesso = len(df_sucesso)
    
    # Adicionar informações ao DataFrame
    df_sucesso.insert(0, 'Status', '✅ Processado')
    df_sucesso.insert(1, 'Data Processamento', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # Nome do arquivo de saída
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    arquivo_saida = f"relatorio_etl_sucesso_{timestamp}.xlsx"
    
    print(f"\n💾 Salvando relatório: {arquivo_saida}")
    
    # Criar o Excel com formatação
    with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
        # Aba com produtos processados com sucesso
        df_sucesso.to_excel(writer, sheet_name='Produtos Processados', index=False)
        
        # Aba com resumo estatístico
        df_resumo = pd.DataFrame({
            'Métrica': [
                'Total de linhas no Excel original',
                'Linhas rejeitadas (com erro)',
                'Linhas processadas com SUCESSO',
                'Taxa de sucesso (%)',
                'Data do processamento'
            ],
            'Valor': [
                total_original,
                total_rejeitadas,
                total_sucesso,
                f"{(total_sucesso / total_original * 100):.2f}%" if total_original > 0 else "0%",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        })
        df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
        
        # Aba com detalhes das rejeições (para referência)
        if not df_rejects.empty:
            df_rejects.to_excel(writer, sheet_name='Detalhes Rejeições', index=False)
        
        # Ajustar largura das colunas
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"\n{'=' * 60}")
    print(f"✅ RELATÓRIO GERADO COM SUCESSO!")
    print(f"{'=' * 60}")
    print(f"📊 ESTATÍSTICAS:")
    print(f"   • Total de produtos no arquivo original: {total_original}")
    print(f"   • Produtos rejeitados (erros): {total_rejeitadas}")
    print(f"   • Produtos processados com SUCESSO: {total_sucesso}")
    print(f"   • Taxa de sucesso: {(total_sucesso / total_original * 100):.2f}%")
    print(f"\n📄 Arquivo gerado: {arquivo_saida}")
    print(f"   • Aba 'Produtos Processados': {total_sucesso} produtos")
    print(f"   • Aba 'Resumo': Estatísticas do processamento")
    print(f"   • Aba 'Detalhes Rejeições': {total_rejeitadas} produtos rejeitados")
    print(f"{'=' * 60}")
    
    return arquivo_saida


if __name__ == "__main__":
    try:
        gerar_relatorio_sucesso()
    except Exception as e:
        print(f"\n❌ ERRO ao gerar relatório: {e}")
        import traceback
        traceback.print_exc()
