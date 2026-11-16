# 샘플 데이터 안내

**이 폴더의 모든 CSV는 기능 시연용 가상 데이터입니다. 공식 환율이 아니며 운영·견적·금융 판단에 사용하지 마세요.**
출력 JSON의 `source: SAMPLE_NOT_OFFICIAL`로도 구분됩니다.

| 파일 | 시나리오 | 목표 괴리율 | 기대 Risk | 기대 결과 JSON |
|---|---|---|---|---|
| `sample_rates.csv` | 기본 샘플 | 약 -1.1% | NORMAL | `docs/sample_result.json` |
| `scenario_normal.csv` | 정상 | 약 -1% | NORMAL | `docs/sample_result_normal.json` |
| `scenario_caution.csv` | 주의 | 약 -5% | CAUTION | `docs/sample_result_caution.json` |
| `scenario_risk.csv` | 위험 | 약 -8.5% | RISK | `docs/sample_result_risk.json` |
| `scenario_critical.csv` | 심각 | 약 -12% | CRITICAL | `docs/sample_result_critical.json` |

시나리오 파일은 `python scripts/make_scenarios.py`로 결정적으로 재생성됩니다.
컬럼: `date`(YYYY-MM-DD), `usd_krw`(양수).
