# Curated results (submitted)

Raw runs land in `runs/` (gitignored). Copy the runs we hand in here:

```bash
cp -R runs/<Task>/<run_id> results/<Task>/
```

- `results/results.csv`: one row per submitted run (copy the rows from `runs/results.csv`)
- `results/labels.csv`: `task,run_id,tag,first_wrong_step,note` for every failed run
- Recordings are **not** in git. Put them on the team drive and link them in the analysis docs.
