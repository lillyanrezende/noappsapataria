-- ============================================================
-- Query para DELETAR warehouse_stock das variantes duplicadas
-- ============================================================
-- Data: 2026-02-27
-- Descrição: Deleta registros de warehouse_stock para as variantes
--           que serão deletadas por terem GTIN duplicado
-- ============================================================

-- PASSO 1: Ver quantos warehouse_stock serão deletados
-- ============================================================

SELECT 
    COUNT(*) as total_warehouse_stock,
    COUNT(DISTINCT variant_id) as variantes_afetadas
FROM warehouse_stock
WHERE variant_id IN (
    488, 489, 490, 491, 492, 495, 496, 501, 504, 505,
    506, 507, 509, 510, 511, 512, 513, 514, 515, 516, 517
);

-- ============================================================
-- PASSO 2: Ver detalhes dos warehouse_stock a deletar
-- ============================================================

SELECT 
    ws.id as warehouse_stock_id,
    ws.variant_id,
    ws.warehouse_id,
    ws.quantity,
    pv.gtin
FROM warehouse_stock ws
LEFT JOIN product_variant pv ON ws.variant_id = pv.id
WHERE ws.variant_id IN (
    488, 489, 490, 491, 492, 495, 496, 501, 504, 505,
    506, 507, 509, 510, 511, 512, 513, 514, 515, 516, 517
)
ORDER BY ws.variant_id;

-- ============================================================
-- PASSO 3: DELETE - REMOVER warehouse_stock
-- ============================================================
-- ⚠️ DESCOMENTE PARA EXECUTAR - ISSO DELETARÁ warehouse_stock!

/*
DELETE FROM warehouse_stock
WHERE variant_id IN (
    488, 489, 490, 491, 492, 495, 496, 501, 504, 505,
    506, 507, 509, 510, 511, 512, 513, 514, 515, 516, 517
);

-- Verificar quantos foram deletados
SELECT 'Warehouse stock deleted successfully' as status;
*/

-- ============================================================
-- PASSO 4: Agora é seguro deletar as variantes
-- ============================================================

/*
DELETE FROM product_variant
WHERE id IN (
    488, 489, 490, 491, 492, 495, 496, 501, 504, 505,
    506, 507, 509, 510, 511, 512, 513, 514, 515, 516, 517
);

-- Verificar quantas foram deletadas
SELECT COUNT(*) as variantes_deletadas
FROM product_variant
WHERE id NOT IN (
    488, 489, 490, 491, 492, 495, 496, 501, 504, 505,
    506, 507, 509, 510, 511, 512, 513, 514, 515, 516, 517
) AND id >= 109;
*/

-- ============================================================
-- PASSO 5: Verificar status final
-- ============================================================

SELECT 
    COUNT(*) as total_warehouse_stock_restantes
FROM warehouse_stock;
