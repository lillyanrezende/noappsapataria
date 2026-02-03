# Guia de Alteração em Massa de Stock

## Como usar a funcionalidade de Alteração em Massa

### 1. Aceder à funcionalidade
- Abre o programa e faz login
- Vai para a aba **"Alterar"**
- Clica no botão **"Alteração em Massa"**

### 2. Preparar lista de produtos

#### Opção A: Digitar manualmente
1. Na janela de Alteração em Massa, escreve os códigos GTIN na área de texto
2. Um GTIN por linha
3. Exemplo:
   ```
   1234567890123
   9876543210987
   5555555555555
   ```

#### Opção B: Carregar de Excel
1. Prepara um arquivo Excel com os GTINs na primeira coluna (coluna A)
2. A primeira linha será ignorada (pode ser o header "GTIN")
3. Clica em **"Carregar de Excel"**
4. Seleciona o arquivo
5. Os GTINs serão carregados automaticamente

**Arquivo de exemplo:** `exemplo_bulk_update.xlsx` (já criado na pasta do programa)

### 3. Configurar a operação

Escolhe as opções:

- **Armazém:** Seleciona o armazém onde o stock será alterado
- **Operação:**
  - **Adicionar:** Soma a quantidade ao stock existente
  - **Remover:** Subtrai a quantidade do stock existente  
  - **Definir:** Define o stock para o valor exato (ignora o valor atual)
- **Quantidade:** Valor a ser usado na operação

### 4. Executar

1. Clica em **"Processar"**
2. Confirma a operação
3. Aguarda o processamento
4. Vê o resultado no log:
   - ✓ = Sucesso
   - ❌ = Erro

### 5. Verificar resultados

O log mostra:
- Quais produtos foram atualizados com sucesso
- Quais tiveram erro (e porquê)
- Resumo final com total de sucessos e erros

## Exemplos de uso

### Exemplo 1: Adicionar 10 unidades a vários produtos
- Lista GTINs: 1234567890123, 9876543210987, ...
- Armazém: Armazém Principal
- Operação: **Adicionar**
- Quantidade: **10**
- Resultado: Cada produto terá +10 unidades

### Exemplo 2: Definir stock de todos para 50
- Lista GTINs: 1234567890123, 9876543210987, ...
- Armazém: Armazém Secundário
- Operação: **Definir**
- Quantidade: **50**
- Resultado: Todos os produtos ficarão com exatamente 50 unidades

### Exemplo 3: Remover 5 unidades
- Lista GTINs: 1234567890123, 9876543210987, ...
- Armazém: Armazém Principal
- Operação: **Remover**
- Quantidade: **5**
- Resultado: Cada produto terá -5 unidades (se houver stock suficiente)

## Notas importantes

⚠️ **Atenção:**
- A operação afeta TODOS os produtos da lista simultaneamente
- Confirma sempre os dados antes de processar
- Se um GTIN não existir, será mostrado erro no log
- A operação **Remover** só funciona se houver stock suficiente
- Todas as alterações são registadas na auditoria do sistema

✅ **Boas práticas:**
- Testa primeiro com poucos produtos
- Verifica o log após processar
- Mantém backup dos dados importantes
- Usa o Excel para facilitar quando há muitos produtos

## Formato do arquivo Excel

```
| GTIN          | Modelo (ref) | Observação  |
|---------------|--------------|-------------|
| 1234567890123 | Modelo A     | Opcional    |
| 9876543210987 | Modelo B     | Opcional    |
| 5555555555555 | Modelo C     | Opcional    |
```

**Nota:** Apenas a primeira coluna (GTIN) é usada. As outras são apenas para referência.

## Resolução de problemas

**Problema:** "GTIN não encontrado"
- **Solução:** Verifica se o código GTIN está correto na base de dados

**Problema:** "Stock insuficiente"
- **Solução:** Ao remover, garante que há stock suficiente ou usa "Definir" em vez de "Remover"

**Problema:** Erro ao carregar Excel
- **Solução:** Verifica se o arquivo está no formato .xlsx e se os GTINs estão na primeira coluna
