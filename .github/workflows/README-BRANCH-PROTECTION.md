# Branch Protection Setup

To enable database commit validation, configure branch protection on the `main` branch:

## Steps

1. Go to: https://github.com/mat-e-exp/ai-pulse/settings/branches
2. Click "Add branch protection rule"
3. Branch name pattern: `main`
4. Enable: **"Require status checks to pass before merging"**
5. Search for and select: `check-database-commit`
6. Enable: **"Require branches to be up to date before merging"** (optional)
7. Click "Create" or "Save changes"

## What This Does

- **Blocks accidental database commits** from local machines
- **Allows scheduled workflow commits** (github-actions[bot])
- **Provides emergency override** via manual workflow dispatch

## How to Override (Emergency Use Only)

When you need to commit database changes manually (e.g., backfilling data, fixing corruption):

1. Make your changes and commit locally
2. Push to GitHub (will fail validation)
3. Go to: Actions → "Validate Database Commits" → "Run workflow"
4. Check the box: "Allow database commit (emergency use only)"
5. Click "Run workflow"
6. Your commit will now be accepted

## Testing

After enabling branch protection, test by:

1. Making a code change (not database): Should push normally ✅
2. Trying to commit `ai_pulse.db`: Should be blocked ❌
3. Using manual override: Should allow commit ✅

## Disabling Protection

If you need to temporarily disable (not recommended):

1. Go to branch protection settings
2. Uncheck "Require status checks"
3. Make your changes
4. Re-enable protection immediately after
