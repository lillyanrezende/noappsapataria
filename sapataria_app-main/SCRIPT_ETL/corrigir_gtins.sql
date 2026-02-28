-- ============================================================
-- Query para corrigir GTINs - Remover últimos 3 caracteres (000)
-- ============================================================
-- Data: 2026-02-27
-- Descrição: Remove os últimos "000" de todos os GTINs a partir da variante_id 109
-- ============================================================

-- PRIMEIRO: Verificar quantos registros serão afetados
SELECT 
    id as variante_id,
    gtin as gtin_atual,
    LEFT(gtin, LENGTH(gtin) - 3) as gtin_corrigido,
    LENGTH(gtin) as tamanho_atual,
    LENGTH(LEFT(gtin, LENGTH(gtin) - 3)) as tamanho_novo
FROM product_variant
WHERE id >= 109
  AND gtin IS NOT NULL
  AND LENGTH(gtin) > 3
  AND RIGHT(gtin, 3) = '000'
ORDER BY id;

-- ============================================================
-- SEGUNDO: Executar a correção (DESCOMENTE PARA EXECUTAR)
-- ============================================================
/*
UPDATE product_variant
SET gtin = LEFT(gtin, LENGTH(gtin) - 3)
WHERE id >= 109
  AND gtin IS NOT NULL
  AND LENGTH(gtin) > 3
  AND RIGHT(gtin, 3) = '000';
*/

-- ============================================================
-- TERCEIRO: Verificar os resultados após a atualização
-- ============================================================
/*
SELECT 
    id as variante_id,
    gtin,
    LENGTH(gtin) as tamanho_gtin
FROM product_variant
WHERE id >= 109
ORDER BY id
LIMIT 50;
*/

-- ============================================================
-- ALTERNATIVA: Query mais segura com validação adicional
-- ============================================================
/*
-- Esta versão só atualiza se:
-- 1. ID >= 109
-- 2. GTIN não é nulo
-- 3. GTIN tem mais de 3 caracteres
-- 4. GTIN termina com '000'
-- 5. Após remover '000', o GTIN ainda tem pelo menos 8 dígitos (válido)

UPDATE product_variant
SET gtin = LEFT(gtin, LENGTH(gtin) - 3),
    updated_at = NOW()
WHERE id >= 109
  AND gtin IS NOT NULL
  AND LENGTH(gtin) > 11  -- Garante que após remover 000, ainda terá >= 8 dígitos
  AND RIGHT(gtin, 3) = '000'
  AND gtin ~ '^[0-9]+$';  -- Garante que só contém números

-- Retornar quantidade de registros atualizados
SELECT COUNT(*) as registros_atualizados
FROM product_variant
WHERE id >= 109
  AND LENGTH(gtin) >= 8
  AND gtin IS NOT NULL;
*/

-- ============================================================
-- ROLLBACK: Caso precise reverter (se tiver backup)
-- ============================================================
/*
-- Esta query só funcionará se você tiver uma tabela de backup
UPDATE product_variant pv
SET gtin = bkp.gtin
FROM product_variant_backup bkp
WHERE pv.id = bkp.id
  AND pv.id >= 109;
*/
