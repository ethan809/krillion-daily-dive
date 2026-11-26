# Deep Dive

An independent, fan-inspired Krillion-style daily quiz. The game follows a seven-question, timed open-answer format with rarity points and depth scoring, but it is **not** affiliated with Krillion and it does not have Krillion's complete answer database.

## Daily questions

- `dist/index.html` is the game.
- `dist/data/daily.json` is a small daily question/score sample.
- `scripts/update_daily.py` checks two public companion pages and validates the date, question text, all seven question cards and example score tiers before writing changes.
- `.github/workflows/update-daily.yml` runs after the official daily reset at 06:20 UTC and commits verified updates. Failed checks leave the previous dataset untouched.
- `.github/workflows/deploy-pages.yml` deploys to GitHub Pages whenever the repository changes.

To deploy: in **Settings → Pages**, select **GitHub Actions** as the build-and-deployment source. Keep the repository private if you want the code hidden. Note that the GitHub Pages website itself will normally be **public**, even when the repository is private.

The quiz automatically falls back to original practice questions if the current day's official prompts have not been verified yet. Local score history remains in the user's browser.
