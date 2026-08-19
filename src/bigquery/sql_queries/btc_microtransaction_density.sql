-- ==============================================================================
-- Query: btc_microtransaction_density.sql
-- Description: Measures the historical decay of everyday microtransactions (<$10, <$500)
--              versus whale transactions (>$50,000) and fee drag.
-- Target: crypto_analytics_mart.btc_daily_utxo_distribution
-- Parameters:
--   @start_date (DATE): Start date of window
--   @end_date (DATE): End date of window
-- ==============================================================================

SELECT
    date,
    total_active_utxos,
    COALESCE(total_tx_count, total_active_utxos) AS total_tx_count,
    micro_tx_count_under_10usd,
    retail_tx_count_10_to_500usd,
    whale_tx_count_over_50kusd,
    (micro_tx_count_under_10usd + retail_tx_count_10_to_500usd + whale_tx_count_over_50kusd) AS total_classified_txs,
    ROUND(
        micro_tx_count_under_10usd * 100.0 / 
        NULLIF((micro_tx_count_under_10usd + retail_tx_count_10_to_500usd + whale_tx_count_over_50kusd), 0),
        2
    ) AS pct_microtransactions,
    ROUND(
        retail_tx_count_10_to_500usd * 100.0 / 
        NULLIF((micro_tx_count_under_10usd + retail_tx_count_10_to_500usd + whale_tx_count_over_50kusd), 0),
        2
    ) AS pct_retail_commerce,
    ROUND(
        whale_tx_count_over_50kusd * 100.0 / 
        NULLIF((micro_tx_count_under_10usd + retail_tx_count_10_to_500usd + whale_tx_count_over_50kusd), 0),
        2
    ) AS pct_whale_institutional,
    avg_fee_usd,
    -- Fee drag on a standard $10 purchase (Fee / $10)
    ROUND(avg_fee_usd / 10.0 * 100.0, 2) AS fee_drag_pct_on_10usd_purchase
FROM
    `{{project_id}}.{{dataset_id}}.btc_daily_utxo_distribution`
WHERE
    date BETWEEN @start_date AND @end_date
ORDER BY
    date ASC;
