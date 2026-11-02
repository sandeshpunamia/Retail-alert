# Reliance regulatory monitor (zero cost)

Emails you (1) instant alerts on government action against Reliance Retail and
(2) a digest of notices/minutes from FSSAI, CAG-FSSAI, Legal Metrology, CDSCO, DPIIT, CPCB.
Runs free on GitHub Actions - your laptop can be off.

## One-time setup (about 10 minutes)
1. **Sender Gmail (free):** use any Gmail account (a new one is fine). Turn on 2-Step Verification,
   then create an App Password: Google Account > Security > App passwords. Copy the 16 characters.
2. **GitHub repo (free):** create a new **private** repo, upload everything in this folder
   (including the hidden `.github` folder).
3. **Add secrets:** Repo > Settings > Secrets and variables > Actions > New repository secret
   - `SMTP_USER` = the sender Gmail address
   - `SMTP_PASS` = the 16-character app password
   - `MAIL_TO`    = sandesh_punamia_lai18@online.isb.edu   (comma-separate to add more)
   - `GEMINI_API_KEY` = *(optional)* free key from aistudio.google.com for better PDF summaries
4. **Test:** Repo > Actions > "Reliance regulatory monitor" > Run workflow. Check your inbox.
   The first run sends a starter digest and then only new items.

## What you receive
| Email | When | Contents |
|---|---|---|
| `ALERT: Reliance - govt action` | hourly, only if new | Reliance group incl. Tira, Hamleys, Milkbasket, Netmeds, RCPL/Campa |
| `Competitor watch` | hourly, only if new | Quick commerce, physical retail, sector-wide actions |
| `Competitor digest` | 4x daily | E-commerce, beauty (Tira competitors), FMCG (RCPL competitors) |
| `Regulatory digest` | 4x daily | Notices/minutes: FSSAI, CAG-FSSAI, Legal Metrology, CDSCO, DPIIT, CPCB |

Schedule (IST): news hourly; digests at 09:10, 13:10, 17:10, 21:10. GitHub may delay runs by 5-30 minutes.
First run is capped (last 24 hours, 5 items per group) so you don't get a flood.

## Tuning
Edit `config.py`: each group's brands, queries and mode (`instant` or `digest`), action words, regulator sources. No other code changes needed.

## Cost and limits
- Free on a private repo up to 2,000 Actions minutes a month. This setup uses roughly 800-1,100.
- Without a Gemini key, summaries are keyword-based extracts, not written prose.
