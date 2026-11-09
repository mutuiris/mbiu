# Runbook: roll back the reference corpus

Use this when a newly published corpus version gives worse results (wrong comparisons, missing standards, bad text) and the previous version was fine.

The API serves exactly one corpus version: the row in `corpus_versions` with `is_active = true`. It reads that version into memory on first use, so a change takes effect after a restart.

## Symptoms

- Artists see many more "Couldn't compare" results, or comparisons that cite the wrong standard, right after the weekly corpus pipeline ran.
- The final summary's `versions.corpus` shows the new version tag.

## Check

In the Supabase dashboard, open **SQL editor** and run:

```sql
select version_tag, is_active, created_at
from corpus_versions
order by created_at desc
limit 5;
```

The active row is the one in use. The row below it is usually the version to go back to.

## Roll back

In the same SQL editor, replace `PREVIOUS_TAG` with the version to restore and run both statements together:

```sql
begin;
update corpus_versions set is_active = false where is_active;
update corpus_versions set is_active = true where version_tag = 'PREVIOUS_TAG';
commit;
```

Only one version can be active at a time; the first statement clears the current one.

Then restart the API so it reads the restored version: Render → **mbiu-api** → **Manual Deploy** → **Restart service**.

## Verify

```bash
curl -f "$API_URL/readyz"
```

It returns `{"status": "ready"}`. Upload a synthetic contract from `evals/datasets/pdfs/` in the web app (never a real contract); the final summary's `versions.corpus` shows `PREVIOUS_TAG`.

## Afterwards

The bad version stays in the table, inactive, for investigation. File a bug for the corpus pipeline with its version tag. The next pipeline run publishes a new version and activates it, so fix the cause before then, or turn the pipeline off with the repository variable `CORPUS_PIPELINE_ENABLED=false`.
