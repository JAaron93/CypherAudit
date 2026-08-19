-- ==============================================================================
-- Query: usdc_eoa_vs_contract.sql
-- Description: Measures counterparty topology: P2P/Merchant (EOA -> EOA)
--              versus DeFi/DEX/Lending (EOA -> Contract).
-- Target: crypto_analytics_mart.usdc_daily_organic_metrics
-- Parameters:
--   @start_date (DATE): Start date of window
--   @end_date (DATE): End date of window
-- ==============================================================================

SELECT
    date,
    ROUND(eoa_to_eoa_volume_usd, 2) AS eoa_to_eoa_volume_usd,
    ROUND(eoa_to_contract_volume_usd, 2) AS eoa_to_contract_volume_usd,
    ROUND(
        eoa_to_eoa_volume_usd * 100.0 / 
        NULLIF((eoa_to_eoa_volume_usd + eoa_to_contract_volume_usd), 0),
        2
    ) AS pct_p2p_merchant_commerce,
    ROUND(
        eoa_to_contract_volume_usd * 100.0 / 
        NULLIF((eoa_to_eoa_volume_usd + eoa_to_contract_volume_usd), 0),
        2
    ) AS pct_defi_smart_contract
FROM
    `{{project_id}}.{{dataset_id}}.usdc_daily_organic_metrics`
WHERE
    date BETWEEN @start_date AND @end_date
ORDER BY
    date ASC;
