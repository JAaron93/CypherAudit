"""BigQuery Batch & Incremental ETL Pipelines for SignalChain Oracle (CypherAudit).

Extracts, transforms, and loads blockchain data from BigQuery Public Datasets:
- `bigquery-public-data.crypto_bitcoin`
- `bigquery-public-data.crypto_ethereum`

into compact, date-partitioned datamart tables:
- `crypto_analytics_mart.btc_daily_utxo_distribution`
- `crypto_analytics_mart.usdc_daily_organic_metrics`

Supports:
1. One-time historical baseline ETL (2014 to 2026).
2. Continuous monthly incremental ETL via MERGE INTO (for 2027, 2028, and beyond).
"""

import os
import re
import calendar
import logging
from typing import Optional
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cypheraudit.etl")


def validate_identifier(name: str, param_name: str) -> str:
    """Validates that a SQL identifier contains only safe alphanumeric characters."""
    if not isinstance(name, str) or not re.match(r"^[a-zA-Z0-9_\-\.]+$", name):
        raise ValueError(f"Invalid SQL identifier for {param_name}: '{name}'")
    return name


def validate_date(date_str: str) -> str:
    """Validates that a date is in YYYY-MM-DD format."""
    if not isinstance(date_str, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError(f"Invalid date format: '{date_str}'")
    return date_str


# DDL and ETL for Bitcoin Datamart (Baseline)
BTC_ETL_SQL = """
CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.btc_daily_utxo_distribution`
PARTITION BY date
CLUSTER BY date
AS
WITH daily_snapshots AS (
  SELECT day AS date
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE('{start_date}'), DATE('{end_date}'), INTERVAL 1 DAY)) AS day
),
active_outputs AS (
  SELECT
    o.tx_hash,
    o.block_timestamp,
    o.spent_block_timestamp,
    o.value / 1e8 AS btc_value,
    DATE(o.block_timestamp) AS creation_date,
    COALESCE(DATE(o.spent_block_timestamp), DATE('9999-12-31')) AS spent_date
  FROM
    `bigquery-public-data.crypto_bitcoin.outputs` o
  WHERE
    DATE(o.block_timestamp) <= '{end_date}'
    AND (o.spent_block_timestamp IS NULL OR DATE(o.spent_block_timestamp) >= '{start_date}')
),
daily_utxo_state AS (
  SELECT
    d.date,
    COUNT(1) AS total_active_utxos,
    SUM(u.btc_value) AS total_active_btc_supply,
    ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) < 1 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_under_1d,
    ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 1 AND DATE_DIFF(d.date, u.creation_date, DAY) < 7 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_1d_to_1w,
    ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 7 AND DATE_DIFF(d.date, u.creation_date, DAY) < 30 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_1w_to_1m,
    ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 30 AND DATE_DIFF(d.date, u.creation_date, DAY) < 180 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_1m_to_6m,
    ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 180 AND DATE_DIFF(d.date, u.creation_date, DAY) < 365 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_6m_to_1y,
    ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 365 AND DATE_DIFF(d.date, u.creation_date, DAY) < 730 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_1y_to_2y,
    ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 730 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_over_2y
  FROM
    daily_snapshots d
  INNER JOIN
    active_outputs u
    ON u.creation_date <= d.date AND u.spent_date > d.date
  GROUP BY
    d.date
),
raw_transactions AS (
  SELECT
    DATE(block_timestamp) AS date,
    tx.hash AS tx_hash,
    tx.fee / 1e8 * 65000.0 AS fee_usd,
    tx.outputs
  FROM
    `bigquery-public-data.crypto_bitcoin.transactions` tx
  WHERE
    DATE(block_timestamp) >= '{start_date}'
    AND DATE(block_timestamp) <= '{end_date}'
),
flattened_tx_outputs AS (
  SELECT
    t.date,
    t.tx_hash,
    t.fee_usd,
    out.value / 1e8 * 65000.0 AS output_usd
  FROM
    raw_transactions t,
    UNNEST(t.outputs) out
),
classified_transactions AS (
  SELECT
    date,
    tx_hash,
    fee_usd,
    SUM(output_usd) AS total_tx_usd,
    CASE WHEN SUM(output_usd) < 10.0 THEN 'micro'
         WHEN SUM(output_usd) BETWEEN 10.0 AND 500.0 THEN 'retail'
         WHEN SUM(output_usd) > 50000.0 THEN 'whale'
         ELSE 'mid' END AS size_class
  FROM
    flattened_tx_outputs
  GROUP BY
    date, tx_hash, fee_usd
),
daily_tx_metrics AS (
  SELECT
    date,
    COUNT(DISTINCT tx_hash) AS total_tx_count,
    COUNTIF(size_class = 'micro') AS micro_tx_count_under_10usd,
    COUNTIF(size_class = 'retail') AS retail_tx_count_10_to_500usd,
    COUNTIF(size_class = 'whale') AS whale_tx_count_over_50kusd,
    AVG(fee_usd) AS avg_fee_usd
  FROM
    classified_transactions
  GROUP BY
    date
)
SELECT
  u.date,
  COALESCE(u.total_active_utxos, 0) AS total_active_utxos,
  COALESCE(u.total_active_btc_supply, 0.0) AS total_active_btc_supply,
  COALESCE(t.total_tx_count, 0) AS total_tx_count,
  COALESCE(u.band_under_1d, 0.0) AS band_under_1d,
  COALESCE(u.band_1d_to_1w, 0.0) AS band_1d_to_1w,
  COALESCE(u.band_1w_to_1m, 0.0) AS band_1w_to_1m,
  COALESCE(u.band_1m_to_6m, 0.0) AS band_1m_to_6m,
  COALESCE(u.band_6m_to_1y, 0.0) AS band_6m_to_1y,
  COALESCE(u.band_1y_to_2y, 0.0) AS band_1y_to_2y,
  COALESCE(u.band_over_2y, 0.0) AS band_over_2y,
  COALESCE(t.micro_tx_count_under_10usd, 0) AS micro_tx_count_under_10usd,
  COALESCE(t.retail_tx_count_10_to_500usd, 0) AS retail_tx_count_10_to_500usd,
  COALESCE(t.whale_tx_count_over_50kusd, 0) AS whale_tx_count_over_50kusd,
  COALESCE(t.avg_fee_usd, 0.0) AS avg_fee_usd
FROM
  daily_utxo_state u
LEFT JOIN
  daily_tx_metrics t ON u.date = t.date;
"""

# DDL and ETL for USDC Datamart (Baseline)
USDC_ETL_SQL = """
CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.usdc_daily_organic_metrics`
PARTITION BY date
CLUSTER BY date
AS
WITH usdc_transfers AS (
  SELECT
    DATE(block_timestamp) AS date,
    DATE_TRUNC(DATE(block_timestamp), MONTH) AS month_bucket,
    from_address,
    to_address,
    SAFE_CAST(value AS NUMERIC) / 1e6 AS amount_usd
  FROM
    `bigquery-public-data.crypto_ethereum.token_transfers`
  WHERE
    token_address = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    AND DATE(block_timestamp) >= '{start_date}'
    AND DATE(block_timestamp) <= '{end_date}'
),
known_contracts AS (
  SELECT DISTINCT address AS contract_address
  FROM `bigquery-public-data.crypto_ethereum.contracts`
),
monthly_wallet_activity AS (
  SELECT
    month_bucket,
    from_address,
    COUNT(1) AS monthly_tx_count,
    SUM(amount_usd) AS monthly_volume_usd
  FROM
    usdc_transfers
  GROUP BY
    month_bucket, from_address
),
filtered_transfers AS (
  SELECT
    t.date,
    t.from_address,
    t.to_address,
    t.amount_usd,
    -- Flag bots and automated contract loops
    CASE 
      WHEN from_kc.contract_address IS NOT NULL THEN FALSE
      WHEN COALESCE(mwa.monthly_tx_count, 0) > 1000 THEN FALSE
      WHEN COALESCE(mwa.monthly_volume_usd, 0) > 10000000.0 THEN FALSE
      ELSE TRUE 
    END AS is_organic,
    -- Flag micro / retail payments
    CASE WHEN t.amount_usd <= 500.0 THEN TRUE ELSE FALSE END AS is_retail,
    -- Flag contract counterparties
    CASE WHEN from_kc.contract_address IS NOT NULL THEN TRUE ELSE FALSE END AS is_from_contract,
    CASE WHEN to_kc.contract_address IS NOT NULL THEN TRUE ELSE FALSE END AS is_to_contract
  FROM
    usdc_transfers t
  LEFT JOIN
    monthly_wallet_activity mwa 
    ON t.from_address = mwa.from_address AND t.month_bucket = mwa.month_bucket
  LEFT JOIN
    known_contracts from_kc ON t.from_address = from_kc.contract_address
  LEFT JOIN
    known_contracts to_kc ON t.to_address = to_kc.contract_address
)
SELECT
  date,
  COUNT(1) AS raw_transfer_count,
  SUM(amount_usd) AS raw_volume_usd,
  COUNTIF(is_organic) AS organic_transfer_count,
  SUM(CASE WHEN is_organic THEN amount_usd ELSE 0 END) AS organic_volume_usd,
  SAFE_DIVIDE(SUM(CASE WHEN is_organic THEN amount_usd ELSE 0 END), SUM(amount_usd)) AS organic_volume_ratio,
  SUM(CASE WHEN is_organic AND is_retail THEN amount_usd ELSE 0 END) AS retail_volume_under_500usd,
  SUM(CASE WHEN is_organic AND NOT is_to_contract THEN amount_usd ELSE 0 END) AS eoa_to_eoa_volume_usd,
  SUM(CASE WHEN is_organic AND is_to_contract THEN amount_usd ELSE 0 END) AS eoa_to_contract_volume_usd,
  SUM(CASE WHEN is_from_contract AND NOT is_to_contract THEN amount_usd ELSE 0 END) AS contract_to_eoa_volume_usd
FROM
  filtered_transfers
  GROUP BY
    date;
"""

# MERGE DDL for Bitcoin Monthly Incremental Ingestion (2027+)
BTC_MONTHLY_MERGE_SQL = """
MERGE `{project_id}.{dataset_id}.btc_daily_utxo_distribution` T
USING (
  WITH daily_snapshots AS (
    SELECT day AS date
    FROM UNNEST(GENERATE_DATE_ARRAY(DATE('{start_date}'), DATE('{end_date}'), INTERVAL 1 DAY)) AS day
  ),
  active_outputs AS (
    SELECT
      o.tx_hash,
      o.block_timestamp,
      o.spent_block_timestamp,
      o.value / 1e8 AS btc_value,
      DATE(o.block_timestamp) AS creation_date,
      COALESCE(DATE(o.spent_block_timestamp), DATE('9999-12-31')) AS spent_date
    FROM
      `bigquery-public-data.crypto_bitcoin.outputs` o
    WHERE
      DATE(o.block_timestamp) <= '{end_date}'
      AND (o.spent_block_timestamp IS NULL OR DATE(o.spent_block_timestamp) >= '{start_date}')
  ),
  daily_utxo_state AS (
    SELECT
      d.date,
      COUNT(1) AS total_active_utxos,
      SUM(u.btc_value) AS total_active_btc_supply,
      ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) < 1 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_under_1d,
      ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 1 AND DATE_DIFF(d.date, u.creation_date, DAY) < 7 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_1d_to_1w,
      ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 7 AND DATE_DIFF(d.date, u.creation_date, DAY) < 30 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_1w_to_1m,
      ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 30 AND DATE_DIFF(d.date, u.creation_date, DAY) < 180 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_1m_to_6m,
      ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 180 AND DATE_DIFF(d.date, u.creation_date, DAY) < 365 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_6m_to_1y,
      ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 365 AND DATE_DIFF(d.date, u.creation_date, DAY) < 730 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_1y_to_2y,
      ROUND(SAFE_DIVIDE(SUM(CASE WHEN DATE_DIFF(d.date, u.creation_date, DAY) >= 730 THEN u.btc_value ELSE 0 END), SUM(u.btc_value)), 4) AS band_over_2y
    FROM
      daily_snapshots d
    INNER JOIN
      active_outputs u
      ON u.creation_date <= d.date AND u.spent_date > d.date
    GROUP BY
      d.date
  ),
  raw_transactions AS (
    SELECT
      DATE(block_timestamp) AS date,
      tx.hash AS tx_hash,
      tx.fee / 1e8 * 65000.0 AS fee_usd,
      tx.outputs
    FROM
      `bigquery-public-data.crypto_bitcoin.transactions` tx
    WHERE
      DATE(block_timestamp) >= '{start_date}'
      AND DATE(block_timestamp) <= '{end_date}'
  ),
  flattened_tx_outputs AS (
    SELECT
      t.date,
      t.tx_hash,
      t.fee_usd,
      out.value / 1e8 * 65000.0 AS output_usd
    FROM
      raw_transactions t,
      UNNEST(t.outputs) out
  ),
  classified_transactions AS (
    SELECT
      date,
      tx_hash,
      fee_usd,
      SUM(output_usd) AS total_tx_usd,
      CASE WHEN SUM(output_usd) < 10.0 THEN 'micro'
           WHEN SUM(output_usd) BETWEEN 10.0 AND 500.0 THEN 'retail'
           WHEN SUM(output_usd) > 50000.0 THEN 'whale'
           ELSE 'mid' END AS size_class
    FROM
      flattened_tx_outputs
    GROUP BY
      date, tx_hash, fee_usd
  ),
  daily_tx_metrics AS (
    SELECT
      date,
      COUNT(DISTINCT tx_hash) AS total_tx_count,
      COUNTIF(size_class = 'micro') AS micro_tx_count_under_10usd,
      COUNTIF(size_class = 'retail') AS retail_tx_count_10_to_500usd,
      COUNTIF(size_class = 'whale') AS whale_tx_count_over_50kusd,
      AVG(fee_usd) AS avg_fee_usd
    FROM
      classified_transactions
    GROUP BY
      date
  )
  SELECT
    u.date,
    COALESCE(u.total_active_utxos, 0) AS total_active_utxos,
    COALESCE(u.total_active_btc_supply, 0.0) AS total_active_btc_supply,
    COALESCE(t.total_tx_count, 0) AS total_tx_count,
    COALESCE(u.band_under_1d, 0.0) AS band_under_1d,
    COALESCE(u.band_1d_to_1w, 0.0) AS band_1d_to_1w,
    COALESCE(u.band_1w_to_1m, 0.0) AS band_1w_to_1m,
    COALESCE(u.band_1m_to_6m, 0.0) AS band_1m_to_6m,
    COALESCE(u.band_6m_to_1y, 0.0) AS band_6m_to_1y,
    COALESCE(u.band_1y_to_2y, 0.0) AS band_1y_to_2y,
    COALESCE(u.band_over_2y, 0.0) AS band_over_2y,
    COALESCE(t.micro_tx_count_under_10usd, 0) AS micro_tx_count_under_10usd,
    COALESCE(t.retail_tx_count_10_to_500usd, 0) AS retail_tx_count_10_to_500usd,
    COALESCE(t.whale_tx_count_over_50kusd, 0) AS whale_tx_count_over_50kusd,
    COALESCE(t.avg_fee_usd, 0.0) AS avg_fee_usd
  FROM
    daily_utxo_state u
  LEFT JOIN
    daily_tx_metrics t ON u.date = t.date
) S
ON T.date = S.date
WHEN MATCHED THEN UPDATE SET
  total_active_utxos = S.total_active_utxos,
  total_active_btc_supply = S.total_active_btc_supply,
  total_tx_count = S.total_tx_count,
  band_under_1d = S.band_under_1d,
  band_1d_to_1w = S.band_1d_to_1w,
  band_1w_to_1m = S.band_1w_to_1m,
  band_1m_to_6m = S.band_1m_to_6m,
  band_6m_to_1y = S.band_6m_to_1y,
  band_1y_to_2y = S.band_1y_to_2y,
  band_over_2y = S.band_over_2y,
  micro_tx_count_under_10usd = S.micro_tx_count_under_10usd,
  retail_tx_count_10_to_500usd = S.retail_tx_count_10_to_500usd,
  whale_tx_count_over_50kusd = S.whale_tx_count_over_50kusd,
  avg_fee_usd = S.avg_fee_usd
WHEN NOT MATCHED THEN INSERT (
  date, total_active_utxos, total_active_btc_supply, total_tx_count, band_under_1d, band_1d_to_1w, band_1w_to_1m,
  band_1m_to_6m, band_6m_to_1y, band_1y_to_2y, band_over_2y,
  micro_tx_count_under_10usd, retail_tx_count_10_to_500usd, whale_tx_count_over_50kusd, avg_fee_usd
) VALUES (
  S.date, S.total_active_utxos, S.total_active_btc_supply, S.total_tx_count, S.band_under_1d, S.band_1d_to_1w, S.band_1w_to_1m,
  S.band_1m_to_6m, S.band_6m_to_1y, S.band_1y_to_2y, S.band_over_2y,
  S.micro_tx_count_under_10usd, S.retail_tx_count_10_to_500usd, S.whale_tx_count_over_50kusd, S.avg_fee_usd
);
"""

# MERGE DDL for USDC Monthly Incremental Ingestion (2027+)
USDC_MONTHLY_MERGE_SQL = """
MERGE `{project_id}.{dataset_id}.usdc_daily_organic_metrics` T
USING (
  WITH usdc_transfers AS (
    SELECT
      DATE(block_timestamp) AS date,
      DATE_TRUNC(DATE(block_timestamp), MONTH) AS month_bucket,
      from_address,
      to_address,
      SAFE_CAST(value AS NUMERIC) / 1e6 AS amount_usd
    FROM
      `bigquery-public-data.crypto_ethereum.token_transfers`
    WHERE
      token_address = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
      AND DATE(block_timestamp) >= '{start_date}'
      AND DATE(block_timestamp) <= '{end_date}'
  ),
  known_contracts AS (
    SELECT DISTINCT address AS contract_address
    FROM `bigquery-public-data.crypto_ethereum.contracts`
  ),
  monthly_wallet_activity AS (
    SELECT
      month_bucket,
      from_address,
      COUNT(1) AS monthly_tx_count,
      SUM(amount_usd) AS monthly_volume_usd
    FROM
      usdc_transfers
    GROUP BY
      month_bucket, from_address
  ),
  filtered_transfers AS (
    SELECT
      t.date,
      t.from_address,
      t.to_address,
      t.amount_usd,
      CASE 
        WHEN from_kc.contract_address IS NOT NULL THEN FALSE
        WHEN COALESCE(mwa.monthly_tx_count, 0) > 1000 THEN FALSE
        WHEN COALESCE(mwa.monthly_volume_usd, 0) > 10000000.0 THEN FALSE
        ELSE TRUE 
      END AS is_organic,
      CASE WHEN t.amount_usd <= 500.0 THEN TRUE ELSE FALSE END AS is_retail,
      CASE WHEN from_kc.contract_address IS NOT NULL THEN TRUE ELSE FALSE END AS is_from_contract,
      CASE WHEN to_kc.contract_address IS NOT NULL THEN TRUE ELSE FALSE END AS is_to_contract
    FROM
      usdc_transfers t
    LEFT JOIN
      monthly_wallet_activity mwa 
      ON t.from_address = mwa.from_address AND t.month_bucket = mwa.month_bucket
    LEFT JOIN
      known_contracts from_kc ON t.from_address = from_kc.contract_address
    LEFT JOIN
      known_contracts to_kc ON t.to_address = to_kc.contract_address
  )
  SELECT
    date,
    COUNT(1) AS raw_transfer_count,
    SUM(amount_usd) AS raw_volume_usd,
    COUNTIF(is_organic) AS organic_transfer_count,
    SUM(CASE WHEN is_organic THEN amount_usd ELSE 0 END) AS organic_volume_usd,
    SAFE_DIVIDE(SUM(CASE WHEN is_organic THEN amount_usd ELSE 0 END), SUM(amount_usd)) AS organic_volume_ratio,
    SUM(CASE WHEN is_organic AND is_retail THEN amount_usd ELSE 0 END) AS retail_volume_under_500usd,
    SUM(CASE WHEN is_organic AND NOT is_to_contract THEN amount_usd ELSE 0 END) AS eoa_to_eoa_volume_usd,
    SUM(CASE WHEN is_organic AND is_to_contract THEN amount_usd ELSE 0 END) AS eoa_to_contract_volume_usd,
    SUM(CASE WHEN is_from_contract AND NOT is_to_contract THEN amount_usd ELSE 0 END) AS contract_to_eoa_volume_usd
  FROM
    filtered_transfers
  GROUP BY
    date
) S
ON T.date = S.date
WHEN MATCHED THEN UPDATE SET
  raw_transfer_count = S.raw_transfer_count,
  raw_volume_usd = S.raw_volume_usd,
  organic_transfer_count = S.organic_transfer_count,
  organic_volume_usd = S.organic_volume_usd,
  organic_volume_ratio = S.organic_volume_ratio,
  retail_volume_under_500usd = S.retail_volume_under_500usd,
  eoa_to_eoa_volume_usd = S.eoa_to_eoa_volume_usd,
  eoa_to_contract_volume_usd = S.eoa_to_contract_volume_usd,
  contract_to_eoa_volume_usd = S.contract_to_eoa_volume_usd
WHEN NOT MATCHED THEN INSERT (
  date, raw_transfer_count, raw_volume_usd, organic_transfer_count,
  organic_volume_usd, organic_volume_ratio, retail_volume_under_500usd,
  eoa_to_eoa_volume_usd, eoa_to_contract_volume_usd, contract_to_eoa_volume_usd
) VALUES (
  S.date, S.raw_transfer_count, S.raw_volume_usd, S.organic_transfer_count,
  S.organic_volume_usd, S.organic_volume_ratio, S.retail_volume_under_500usd,
  S.eoa_to_eoa_volume_usd, S.eoa_to_contract_volume_usd, S.contract_to_eoa_volume_usd
);
"""


BTC_TABLE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.btc_daily_utxo_distribution` (
  date DATE,
  total_active_utxos INT64,
  total_active_btc_supply NUMERIC,
  total_tx_count INT64,
  band_under_1d FLOAT64,
  band_1d_to_1w FLOAT64,
  band_1w_to_1m FLOAT64,
  band_1m_to_6m FLOAT64,
  band_6m_to_1y FLOAT64,
  band_1y_to_2y FLOAT64,
  band_over_2y FLOAT64,
  micro_tx_count_under_10usd INT64,
  retail_tx_count_10_to_500usd INT64,
  whale_tx_count_over_50kusd INT64,
  avg_fee_usd FLOAT64
)
PARTITION BY date
CLUSTER BY date;
"""

USDC_TABLE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset_id}.usdc_daily_organic_metrics` (
  date DATE,
  raw_transfer_count INT64,
  raw_volume_usd NUMERIC,
  organic_transfer_count INT64,
  organic_volume_usd NUMERIC,
  organic_volume_ratio FLOAT64,
  retail_volume_under_500usd NUMERIC,
  eoa_to_eoa_volume_usd NUMERIC,
  eoa_to_contract_volume_usd NUMERIC,
  contract_to_eoa_volume_usd NUMERIC
)
PARTITION BY date
CLUSTER BY date;
"""


def run_etl_pipeline(
    project_id: str,
    dataset_id: str = "crypto_analytics_mart",
    start_date: str = "2014-01-01",
    end_date: str = "2026-01-01",
    max_bytes_billed: int = 100_000_000_000,  # 100 GB strict billing ceiling per annual batch job
    chunk_by_year: bool = True,
    dry_run: bool = False,
):
    """Executes or dry-runs the baseline BigQuery Batch ETL pipeline (2014–2026) in bounded annual chunks."""
    clean_project = validate_identifier(project_id, "project_id")
    clean_dataset = validate_identifier(dataset_id, "dataset_id")
    clean_start = validate_date(start_date)
    clean_end = validate_date(end_date)

    client = bigquery.Client(project=clean_project)

    dataset_ref = bigquery.DatasetReference(clean_project, clean_dataset)
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset {clean_dataset} already exists.")
    except Exception:
        logger.info(f"Creating dataset {clean_dataset} in {clean_project}...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset, exists_ok=True)

    # Ensure tables exist with partition/cluster definitions
    if not dry_run:
        client.query(BTC_TABLE_SCHEMA_SQL.format(project_id=clean_project, dataset_id=clean_dataset)).result()
        client.query(USDC_TABLE_SCHEMA_SQL.format(project_id=clean_project, dataset_id=clean_dataset)).result()

    job_config = bigquery.QueryJobConfig(
        dry_run=dry_run,
        maximum_bytes_billed=max_bytes_billed if not dry_run else None,
    )

    start_year = int(clean_start[:4])
    end_year = int(clean_end[:4])

    if chunk_by_year and start_year < end_year:
        for year in range(start_year, end_year + 1):
            y_start = f"{year:04d}-01-01" if year == start_year else f"{year:04d}-01-01"
            y_end = clean_end if year == end_year else f"{year:04d}-12-31"
            if y_start > y_end:
                continue

            btc_merge = BTC_MONTHLY_MERGE_SQL.format(
                project_id=clean_project, dataset_id=clean_dataset, start_date=y_start, end_date=y_end
            )
            usdc_merge = USDC_MONTHLY_MERGE_SQL.format(
                project_id=clean_project, dataset_id=clean_dataset, start_date=y_start, end_date=y_end
            )

            for name, sql in [(f"Bitcoin {year} Annual Batch", btc_merge), (f"USDC {year} Annual Batch", usdc_merge)]:
                logger.info(f"Submitting {name} (dry_run={dry_run}, max_bytes_billed={max_bytes_billed})...")
                query_job = client.query(sql, job_config=job_config)
                if dry_run:
                    logger.info(f"[{name}] Estimated Bytes: {query_job.total_bytes_processed / (1024**3):.2f} GB")
                else:
                    logger.info(f"[{name}] Job started: {query_job.job_id}")
    else:
        btc_sql = BTC_MONTHLY_MERGE_SQL.format(
            project_id=clean_project, dataset_id=clean_dataset, start_date=clean_start, end_date=clean_end
        )
        usdc_sql = USDC_MONTHLY_MERGE_SQL.format(
            project_id=clean_project, dataset_id=clean_dataset, start_date=clean_start, end_date=clean_end
        )
        for name, sql in [("Bitcoin Baseline Batch", btc_sql), ("USDC Baseline Batch", usdc_sql)]:
            logger.info(f"Submitting {name} (dry_run={dry_run}, max_bytes_billed={max_bytes_billed})...")
            query_job = client.query(sql, job_config=job_config)
            if dry_run:
                logger.info(f"[{name}] Estimated Bytes: {query_job.total_bytes_processed / (1024**3):.2f} GB")
            else:
                logger.info(f"[{name}] Job started: {query_job.job_id}")


def run_monthly_incremental_etl(
    project_id: str,
    dataset_id: str = "crypto_analytics_mart",
    target_year: int = 2026,
    target_month: int = 1,
    max_bytes_billed: int = 50_000_000_000,  # 50 GB ceiling for single-month delta
    dry_run: bool = False,
):
    """Executes incremental MERGE INTO for a single calendar month (e.g. for continuous ingestion in 2027+)."""
    clean_project = validate_identifier(project_id, "project_id")
    clean_dataset = validate_identifier(dataset_id, "dataset_id")

    _, last_day = calendar.monthrange(target_year, target_month)
    start_date = f"{target_year:04d}-{target_month:02d}-01"
    end_date = f"{target_year:04d}-{target_month:02d}-{last_day:02d}"

    logger.info(f"Executing monthly incremental ETL for window {start_date} to {end_date}")

    client = bigquery.Client(project=clean_project)

    btc_merge_sql = BTC_MONTHLY_MERGE_SQL.format(
        project_id=clean_project, dataset_id=clean_dataset, start_date=start_date, end_date=end_date
    )
    usdc_merge_sql = USDC_MONTHLY_MERGE_SQL.format(
        project_id=clean_project, dataset_id=clean_dataset, start_date=start_date, end_date=end_date
    )

    job_config = bigquery.QueryJobConfig(
        dry_run=dry_run,
        maximum_bytes_billed=max_bytes_billed if not dry_run else None,
    )

    for name, sql in [("Bitcoin Monthly MERGE", btc_merge_sql), ("USDC Monthly MERGE", usdc_merge_sql)]:
        logger.info(f"Submitting {name} incremental job (dry_run={dry_run})...")
        query_job = client.query(sql, job_config=job_config)
        if dry_run:
            logger.info(f"[{name}] Estimated Bytes to Process: {query_job.total_bytes_processed / (1024**3):.2f} GB")
        else:
            logger.info(f"[{name}] Incremental Merge Job started: {query_job.job_id}")


if __name__ == "__main__":
    proj = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
    logger.info(f"Running ETL Pipeline for project: {proj}")
    run_etl_pipeline(project_id=proj, dry_run=True)
