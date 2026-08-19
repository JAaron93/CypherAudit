-- ==============================================================================
-- Query: usdc_organic_vs_noise.sql
-- Description: Measures organic everyday volume vs bot/MEV/wash volume for USDC
--              using the Visa/Artemis noise-filter methodology.
-- Target: crypto_analytics_mart.usdc_daily_organic_metrics
-- Parameters:
--   @start_date (DATE): Start date of window
--   @end_date (DATE): End date of window
-- ==============================================================================

SELECT
    date,
    raw_transfer_count,
    organic_transfer_count,
    ROUND(raw_volume_usd, 2) AS raw_volume_usd,
    ROUND(organic_volume_usd, 2) AS organic_volume_usd,
    ROUND(organic_volume_ratio * 100.0, 2) AS organic_volume_pct,
    ROUND((1.0 - organic_volume_ratio) * 100.0, 2) AS automated_noise_pct,
    ROUND(retail_volume_under_500usd, 2) AS retail_volume_under_500usd,
    ROUND(
        retail_volume_under_500usd * 100.0 / NULLIF(organic_volume_usd, 0),
        2
    ) AS pct_retail_of_organic
FROM
    `{{project_id}}.{{dataset_id}}.usdc_daily_organic_metrics`
WHERE
    date BETWEEN @start_date AND @end_date
ORDER BY
    date ASC;
