# Governed Building AI

**Building AI that its occupants can see, govern and repair.**

AI is starting to run the buildings we live in: it decides cooling, ventilation and fresh air in schools, clinics and offices. Today the people inside have no say. The logic sits with the vendor, the data leaves the building, and nobody can explain or correct what the system does.

This project is an open governance layer that sits between any building AI and the equipment:

1. **Rules written by the building's own people**, in an open, readable format ([Building Rules Format v0.1](spec/RULES_FORMAT.md)).
2. **Every AI decision checked and explained** in plain language. Proposals that break a hard rule are corrected; soft rules give way only when a hard rule needs it.
3. **Correct and retrain on site.** In recommendation mode, staff review the AI's changes; each override updates the AI's preferences, so it needs fewer corrections.
4. **Data stays in the building**, under terms the community sets.

It never needs to see inside the AI. It only checks what the AI proposes, so it works with any vendor's controller.

## Prototype results (simulation)

The same predictive AI controller runs the same simulated school block (600 m2, 120 occupants) over three synthetic hot-season days shaped like a Riyadh summer:

| Setup | Hours above 25.5 C in class, per day | Hottest classroom | Average CO2 in class | Electricity per day | Staff overrides, day 1/2/3 |
|---|---|---|---|---|---|
| 1. Vendor AI alone | 7.0 h | 31.8 C | 3,134 ppm | 75 kWh | none possible |
| 2. Same AI + community rules | 0.25 h | 26.6 C | 965 ppm | 142 kWh | none |
| 3. Rules + staff feedback | 0.08 h | 26.6 C | 965 ppm | 150 kWh | 8 / 1 / 1 |

The vendor-tuned AI uses the least electricity because it lets classrooms overheat and cuts fresh air. The community's rules trade that energy for health and comfort, and every trade is logged with a reason. With staff feedback, overrides fall from 8 on day 1 to 1 a day as the AI learns.

These numbers come from an illustrative model, not a real building. All parameters are in [`gba/building.py`](gba/building.py).

## Run it

```bash
pip install -r requirements.txt
python run_demo.py         # writes results/summary.json, decision logs, results/demo.html
python -m pytest -q        # tests
```

Open `results/demo.html` in a browser for the interactive demo.

## Repository

| Path | What it is |
|---|---|
| `rules/school_riyadh_example.yaml` | Example rules file written for a demo school |
| `spec/RULES_FORMAT.md` | The open Building Rules Format v0.1 |
| `gba/building.py` | Transparent single-zone thermal and CO2 model |
| `gba/controller.py` | Predictive "vendor-style" AI controller with learnable preferences |
| `gba/governance.py` | The governance layer: rule enforcement and plain-language explanations |
| `gba/scenarios.py` | Runs autonomous, governed and recommendation modes |
| `gba/dashboard.py` | Builds the single-file demo page |

## Roadmap

- Adapters for real building protocols (BACnet, Modbus), read-only first
- Pilot in a public building in Riyadh, in recommendation-only mode
- Arabic explanations; a simple rules editor for non-engineers
- Shared, open device library and consent-based dataset
- Model tender clauses so public buildings can require open rules and owner-held data

## License

Code: MIT. Documentation and the rules format: CC BY 4.0.
