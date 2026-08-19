-- ==============================================================================
-- Query: btc_utxo_hodl_waves.sql
-- Description: Retrieves daily Bitcoin UTXO age distributions (HODL Waves)
-- Target: crypto_analytics_mart.btc_daily_utxo_distribution
-- Parameters:
--   @start_date (DATE): Start of analysis window
--   @end_date (DATE): End of analysis window
-- ==============================================================================

SELECT
    date,
    total_active_utxos,
    ROUND(band_under_1d * 100.0, 2) AS pct_under_1d,
    ROUND(band_1d_to_1w * 100.0, 2) AS pct_1d_to_1w,
    ROUND(band_1w_to_1m * 100.0, 2) AS pct_1w_to_1m,
    ROUND(band_1m_to_6m * 100.0, 2) AS pct_1m_to_6m,
    ROUND(band_6m_to_1y * 100.0, 2) AS pct_6m_to_1y,
    ROUND(band_1y_to_2y * 100.0, 2) AS pct_1y_to_2y,
    ROUND(band_over_2y * 100.0, 2) AS pct_over_2y,
    ROUND((band_1y_to_2y + band_over_2y) * 100.0, 2) AS pct_dormant_supply_over_1y
FROM
    `{{project_id}}.{{dataset_id}}.btc_daily_utxo_distribution`
WHERE
    date BETWEEN @start_date AND @end_date
ORDER BY
    date ASC;
