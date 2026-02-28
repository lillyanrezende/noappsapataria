-- ============================================================
-- Query SQL para DELETAR VARIANTES com GTINs Duplicados
-- Versão com tratamento de Foreign Key (warehouse_stock)
-- ============================================================
-- Data: 2026-02-27
-- Problema: warehouse_stock tem constraint FK para product_variant
-- Solução: Deletar warehouse_stock PRIMEIRO, depois product_variant
-- ============================================================

-- PASSO 1: IDENTIFICAR GTINs que serão DUPLICADOS após a correção
-- ============================================================

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
-- PASSO 3: Ver warehouse_stock que precisam ser deletados
-- ============================================================

SELECT 
    ws.id as warehouse_stock_id,
    ws.variant_id as variante_id,
    pv.gtin,
    ws.quantity
FROM warehouse_stock ws
INNER JOIN product_variant pv ON ws.variant_id = pv.id
WHERE EXISTS (
    SELECT 1
    FROM product_variant pv1
    INNER JOIN product_variant pv2 
        ON LEFT(pv1.gtin, LENGTH(pv1.gtin) - 3) = pv2.gtin
        AND pv1.id != pv2.id
    WHERE pv1.id = ws.variant_id
      AND pv1.id >= 109
      AND pv1.gtin IS NOT NULL
      AND LENGTH(pv1.gtin) > 11
      AND RIGHT(pv1.gtin, 3) = '000'
      AND pv2.gtin IS NOT NULL
)
ORDER BY ws.variant_id;

-- ============================================================
-- PASSO 4A: DELETE warehouse_stock (ORDEM CORRETA!)
-- ============================================================
-- ⚠️ DESCOMENTE E EXECUTE PRIMEIRO - Esto Deletará warehouse_stock!
-- Sem deletar warehouse_stock primeiro, o DELETE de product_variant falhará!

/*
DELETE FROM warehouse_stock ws
WHERE ws.variant_id IN (
    SELECT DISTINCT pv1.id
    FROM product_variant pv1
    INNER JOIN product_variant pv2 
        ON LEFT(pv1.gtin, LENGTH(pv1.gtin) - 3) = pv2.gtin
        AND pv1.id != pv2.id
    WHERE pv1.id >= 109
      AND pv1.gtin IS NOT NULL
      AND LENGTH(pv1.gtin) > 11
      AND RIGHT(pv1.gtin, 3) = '000'
      AND pv2.gtin IS NOT NULL
);

-- Verificar quantos foram deletados
SELECT 'Registros warehouse_stock deletados' as status;
*/

-- ============================================================
-- PASSO 4B: DELETE product_variant (APÓS deletar warehouse_stock)
-- ============================================================
-- ⚠️ DESCOMENTE E EXECUTE SEGUNDO - Isto Deletará product_variant!
-- Só é seguro executar APÓS deletar warehouse_stock!

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

-- Verificar quantas foram deletadas
SELECT COUNT(*) as variantes_deletadas
FROM product_variant
WHERE id >= 109;
*/

-- ============================================================
-- PASSO 5: CORRIGIR GTINs das variantes restantes
-- ============================================================
-- ⚠️ DESCOMENTE E EXECUTE TERCEIRO - Isto Corrigirá os GTINs!

/*
UPDATE product_variant
SET gtin = LEFT(gtin, LENGTH(gtin) - 3),
    updated_at = NOW()
WHERE id >= 109
  AND gtin IS NOT NULL
  AND LENGTH(gtin) > 3
  AND RIGHT(gtin, 3) = '000';

-- Verificar quantas foram atualizadas
SELECT COUNT(*) as gtins_corrigidos
FROM product_variant
WHERE id >= 109
  AND gtin IS NOT NULL
  AND NOT RIGHT(gtin, 3) = '000';
*/

-- ============================================================
-- PASSO 6: Verificar resultados finais
-- ============================================================

-- Contar variantes restantes
SELECT COUNT(*) as total_variantes_restantes
FROM product_variant
WHERE id >= 109;

-- Verificar se ainda existem duplicatas
SELECT 
    gtin,
    COUNT(*) as quantidade,
    STRING_AGG(CAST(id AS TEXT), ', ') as variante_ids
FROM product_variant
WHERE gtin IS NOT NULL
  AND id >= 109
GROUP BY gtin
HAVING COUNT(*) > 1
ORDER BY quantidade DESC;

-- Ver GTINs corrigidos (amostra)
SELECT 
    id,
    gtin,
    LENGTH(gtin) as tamanho_gtin,
    CASE 
        WHEN RIGHT(gtin, 3) = '000' THEN 'PRECISA CORRIGER'
        ELSE 'OK'
    END as status_gtin
FROM product_variant
WHERE id >= 109
ORDER BY id
LIMIT 50;
