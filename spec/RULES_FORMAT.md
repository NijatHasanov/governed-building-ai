# Building Rules Format v0.1

A plain, human-readable file in which the people who use a building state how its automated systems may behave. Any controller, from any vendor, can follow it. Licensed CC BY 4.0.

## Design goals

- Readable and writable by facilities staff, not only engineers.
- Vendor-neutral: it constrains actions, not algorithms.
- Every rule has an id and a description, so every intervention can be explained.
- Explicit priorities: `hard` rules always win, `soft` rules yield to hard rules, `alert` rules notify people.

## Structure

```yaml
format: building-rules/0.1
building: { name, location, zones }
authors: [ { role } ]
schedule:
  occupied: { days, from, to }
  precool_window: { from, to }
rules:
  - id: unique-id
    description: "Plain sentence shown in every explanation"
    when: occupied | unoccupied | always
    severity: hard | soft | alert
    limit:  { ... }    # constraints on actions
    target: { ... }    # outcomes to watch (alert rules)
decision_mode: recommend | supervised | autonomous
explanations: { language: [en, ar], log_every_decision: true }
data_terms:
  occupancy_data: { stays_on_site, retention_days, sharing, withdrawable }
```

## Supported keys in v0.1

| Key | Kind | Meaning |
|---|---|---|
| `setpoint_max_c` | limit | Highest allowed cooling setpoint; also forces cooling on when it applies |
| `setpoint_min_c` | limit | Lowest allowed setpoint (no overcooling) |
| `fresh_air_lps_per_person_min` | limit | Minimum outdoor air per occupant, litres per second |
| `cooling_allowed_only_in` | limit | Name of a schedule window outside which cooling must stay off when unoccupied |
| `cooling_power_kw_max` | limit | Electricity cap for cooling; normally `soft` |
| `co2_ppm_max` | target | CO2 level above which staff are alerted |

Unknown keys are rejected, so a file never silently means less than its authors think.

## Open questions for v0.2

Multiple zones, rule authorship and approval records, per-rule review dates, multilingual descriptions, and mapping to existing building data models such as Project Haystack.
