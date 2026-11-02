// Synthetic native usage only; never imported by production code.
export const fixture = {
  "dashboard": {
    "schema_version": 1,
    "kpis": {
      "schema_version": 1,
      "total_cost": {
        "value": "0.000016",
        "unit": "money",
        "basis": "estimated",
        "currency": "USD",
        "source": "https://developers.openai.com/api/docs/pricing",
        "scope": "telecom_workspace",
        "observed_at": "2026-11-02T12:00:00Z",
        "window": {
          "start": "2026-10-26T12:00:00Z",
          "end": "2026-11-02T12:00:00Z"
        },
        "coverage": "partial",
        "reason": "Standard uncached scenario; excludes other fees"
      },
      "observed_tokens": {
        "value": "30",
        "unit": "tokens",
        "basis": "observed",
        "currency": null,
        "source": "agent_engine_cost_dashboard",
        "scope": "telecom_workspace",
        "observed_at": "2026-11-02T12:00:00Z",
        "window": {
          "start": "2026-10-26T12:00:00Z",
          "end": "2026-11-02T12:00:00Z"
        },
        "coverage": "partial",
        "reason": "Native period aggregate; exact boundary/deduplication unverified"
      },
      "average_cost_per_execution": {
        "value": null,
        "unit": "money",
        "basis": "unavailable",
        "currency": "USD",
        "source": "agent_engine_cost_dashboard",
        "scope": "telecom_workspace",
        "observed_at": "2026-11-02T12:00:00Z",
        "window": {
          "start": "2026-10-26T12:00:00Z",
          "end": "2026-11-02T12:00:00Z"
        },
        "coverage": "unknown",
        "reason": "No execution denominator"
      },
      "cache_hit_ratio": {
        "value": null,
        "unit": "ratio",
        "basis": "unavailable",
        "currency": null,
        "source": "agent_engine_cost_dashboard",
        "scope": "telecom_workspace",
        "observed_at": "2026-11-02T12:00:00Z",
        "window": {
          "start": "2026-10-26T12:00:00Z",
          "end": "2026-11-02T12:00:00Z"
        },
        "coverage": "unknown",
        "reason": "No eligible retrieval-cache lookup counts"
      },
      "token_goodput": {
        "value": null,
        "unit": "ratio",
        "basis": "unavailable",
        "currency": null,
        "source": "agent_engine_cost_dashboard",
        "scope": "telecom_workspace",
        "observed_at": "2026-11-02T12:00:00Z",
        "window": {
          "start": "2026-10-26T12:00:00Z",
          "end": "2026-11-02T12:00:00Z"
        },
        "coverage": "unknown",
        "reason": "No token/outcome attribution"
      },
      "execution_count": {
        "value": null,
        "unit": "executions",
        "basis": "unavailable",
        "currency": null,
        "source": "agent_engine_cost_dashboard",
        "scope": "telecom_workspace",
        "observed_at": "2026-11-02T12:00:00Z",
        "window": {
          "start": "2026-10-26T12:00:00Z",
          "end": "2026-11-02T12:00:00Z"
        },
        "coverage": "unknown",
        "reason": "LLM calls are not executions"
      },
      "partial": true
    },
    "applications": {
      "status": "partial",
      "rows": [
        {
          "key": "telecom_workspace",
          "metric": {
            "value": "30",
            "unit": "tokens",
            "basis": "observed",
            "currency": null,
            "source": "agent_engine_cost_dashboard",
            "scope": "telecom_workspace",
            "observed_at": "2026-11-02T12:00:00Z",
            "window": {
              "start": "2026-10-26T12:00:00Z",
              "end": "2026-11-02T12:00:00Z"
            },
            "coverage": "partial",
            "reason": "Native period aggregate; exact boundary/deduplication unverified"
          }
        }
      ],
      "reason": "Native aggregates only; missing observations are not zero"
    },
    "daily": {
      "status": "partial",
      "rows": [
        {
          "key": "2026-11-01",
          "metric": {
            "value": "30",
            "unit": "tokens",
            "basis": "observed",
            "currency": null,
            "source": "agent_engine_cost_dashboard",
            "scope": "telecom_workspace",
            "observed_at": "2026-11-02T12:00:00Z",
            "window": {
              "start": "2026-10-26T12:00:00Z",
              "end": "2026-11-02T12:00:00Z"
            },
            "coverage": "partial",
            "reason": "Native period aggregate; exact boundary/deduplication unverified"
          }
        }
      ],
      "reason": "Native aggregates only; missing observations are not zero"
    },
    "anomalies": {
      "status": "unavailable",
      "rows": [],
      "reason": "Complete comparable daily baseline absent"
    },
    "context": {
      "status": "unavailable",
      "rows": [],
      "reason": "Not attributed by native cost source"
    },
    "token_categories": {
      "status": "partial",
      "rows": [
        {
          "key": "input",
          "metric": {
            "value": "20",
            "unit": "tokens",
            "basis": "observed",
            "currency": null,
            "source": "agent_engine_cost_dashboard",
            "scope": "telecom_workspace",
            "observed_at": "2026-11-02T12:00:00Z",
            "window": {
              "start": "2026-10-26T12:00:00Z",
              "end": "2026-11-02T12:00:00Z"
            },
            "coverage": "partial",
            "reason": "Native period aggregate; exact boundary/deduplication unverified"
          }
        },
        {
          "key": "output",
          "metric": {
            "value": "10",
            "unit": "tokens",
            "basis": "observed",
            "currency": null,
            "source": "agent_engine_cost_dashboard",
            "scope": "telecom_workspace",
            "observed_at": "2026-11-02T12:00:00Z",
            "window": {
              "start": "2026-10-26T12:00:00Z",
              "end": "2026-11-02T12:00:00Z"
            },
            "coverage": "partial",
            "reason": "Native period aggregate; exact boundary/deduplication unverified"
          }
        },
        {
          "key": "cached_input",
          "metric": {
            "value": null,
            "unit": "tokens",
            "basis": "unavailable",
            "currency": null,
            "source": "agent_engine_cost_dashboard",
            "scope": "telecom_workspace",
            "observed_at": "2026-11-02T12:00:00Z",
            "window": {
              "start": "2026-10-26T12:00:00Z",
              "end": "2026-11-02T12:00:00Z"
            },
            "coverage": "unknown",
            "reason": "Cache split unavailable"
          }
        }
      ],
      "reason": "Native aggregates only; missing observations are not zero"
    },
    "models": {
      "status": "partial",
      "rows": [
        {
          "key": "gpt-5.6-luna",
          "metric": {
            "value": "30",
            "unit": "tokens",
            "basis": "observed",
            "currency": null,
            "source": "agent_engine_cost_dashboard",
            "scope": "telecom_workspace",
            "observed_at": "2026-11-02T12:00:00Z",
            "window": {
              "start": "2026-10-26T12:00:00Z",
              "end": "2026-11-02T12:00:00Z"
            },
            "coverage": "partial",
            "reason": "Native period aggregate; exact boundary/deduplication unverified"
          }
        }
      ],
      "reason": "Native aggregates only; missing observations are not zero"
    },
    "agents": {
      "status": "unavailable",
      "rows": [],
      "reason": "Not attributed by native cost source"
    },
    "intents": {
      "status": "unavailable",
      "rows": [],
      "reason": "Not attributed by native cost source"
    },
    "estimate": {
      "amount_usd": "0.000016",
      "basis": "estimated",
      "price": {
        "provider": "openai",
        "model": "gpt-5.6-luna",
        "source_url": "https://developers.openai.com/api/docs/pricing",
        "checked_at": "2026-11-02T01:03:15Z",
        "currency": "USD",
        "input_per_million": "0.20",
        "output_per_million": "1.20",
        "context_band": "short",
        "service_tier": "standard"
      },
      "assumptions": [
        "All input treated as regular uncached input; cache reads/writes unknown",
        "Standard service, short context assumed per request",
        "No regional uplift, gateway markup, discounts, taxes or non-token charges",
        "Current price snapshot; historical tariff effectiveness not verified"
      ]
    }
  },
  "focus": {
    "schema_version": 1,
    "records": [],
    "next_cursor": null,
    "status": "unavailable",
    "reason": "Native source has no billed event/SKU records"
  }
};
