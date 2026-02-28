-- ============================================================
-- Query para EXCLUIR VARIANTES com GTINs Duplicados
-- ============================================================
-- Data: 2026-02-27
-- Descrição: Identifica e exclui variantes cujos GTINs (após remover 000)
--           já existem em outras variantes
-- ============================================================

-- PASSO 1: IDENTIFICAR GTINs que serão DUPLICADOS após a correção
-- ============================================================
-- Esta query mostra quais GTINs corrigidos já existem

SELECT 
    pv1.id as variante_duplicada_id,
    pv1.gtin as gtin_com_000,
    LEFT(pv1.gtin, LENGTH(pv1.gtin) - 3) as gtin_corrigido,
    pv1.model_id,
    pv2.id as variante_existente_id,
    pv2.gtin as gtin_ja_existe,
    pv2.model_id as modelo_existente
FROM product_variant pv1
INNER JOIN product_variant pv2 
    ON LEFT(pv1.gtin, LENGTH(pv1.gtin) - 3) = pv2.gtin
    AND pv1.id != pv2.id
WHERE pv1.id >= 109
  AND pv1.gtin IS NOT NULL
  AND LENGTH(pv1.gtin) > 11
  AND RIGHT(pv1.gtin, 3) = '000'
  AND pv2.gtin IS NOT NULL
ORDER BY gtin_corrigido, pv1.id;

-- ============================================================
-- PASSO 2: Contar quantas variantes serão deletadas
-- ============================================================

SELECT COUNT(DISTINCT pv1.id) as total_variantes_para_deletar
FROM product_variant pv1
INNER JOIN product_variant pv2 
    ON LEFT(pv1.gtin, LENGTH(pv1.gtin) - 3) = pv2.gtin
    AND pv1.id != pv2.id
WHERE pv1.id >= 109
  AND pv1.gtin IS NOT NULL
  AND LENGTH(pv1.gtin) > 11
  AND RIGHT(pv1.gtin, 3) = '000'
  AND pv2.gtin IS NOT NULL;

-- ============================================================
-- PASSO 3: DELETE - REMOVER VARIANTES COM GTINS DUPLICADOS
-- ============================================================
-- ⚠️ DESCOMENTE PARA EXECUTAR - ISSO DELETARÁ REGISTROS!
-- ============================================================

/*
DELETE FROM product_variant pv1
WHERE pv1.id >= 109
  AND pv1.gtin IS NOT NULL
  AND LENGTH(pv1.gtin) > 11
  AND RIGHT(pv1.gtin, 3) = '000'
  AND EXISTS (
      SELECT 1
      FROM product_variant pv2
      WHERE LEFT(pv1.gtin, LENGTH(pv1.gtin) - 3) = pv2.gtin
        AND pv1.id != pv2.id
        AND pv2.gtin IS NOT NULL
  );
*/

-- ============================================================
-- PASSO 4: Verificar o status após a operação
-- ============================================================

/*
-- Contar variantes restantes
SELECT COUNT(*) as total_variantes_restantes
FROM product_variant
WHERE id >= 109;

-- Verificar se ainda existem duplicatas
SELECT 
    gtin,
    COUNT(*) as quantidade
FROM product_variant
WHERE gtin IS NOT NULL
  AND id >= 109
GROUP BY gtin
HAVING COUNT(*) > 1
ORDER BY quantidade DESC;
*/

-- ============================================================
-- ALTERNATIVA: Se preferir manter um registro e delegar ao Python
-- ============================================================
-- Ver quais variantes precisam ser deletadas
SELECT 
    pv1.id as variante_id_para_deletar,
    pv1.gtin as gtin_atual,
    LEFT(pv1.gtin, LENGTH(pv1.gtin) - 3) as gtin_corrigido,
    pv1.model_id,
    pv2.id as variante_id_que_mantem,
    pv2.gtin as gtin_existente
FROM product_variant pv1
INNER JOIN product_variant pv2 
    ON LEFT(pv1.gtin, LENGTH(pv1.gtin) - 3) = pv2.gtin
    AND pv1.id != pv2.id
WHERE pv1.id >= 109
  AND pv1.gtin IS NOT NULL
  AND LENGTH(pv1.gtin) > 11
  AND RIGHT(pv1.gtin, 3) = '000'
  AND pv2.gtin IS NOT NULL
ORDER BY gtin_corrigido, pv1.id;
