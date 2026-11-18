# Your checks in the app — 2026-11-18

These features are built and pass their automated tests on synthetic data. They can be marked done only when you
have tried them in your own app (http://127.0.0.1:8000) and they behave as described. Each check takes a few minutes.
Tell ALFRED's developer "FIN-06 pass" or "FIN-06 fail: <what you saw>"; the result is recorded against that item.

Nothing here moves money, trades, books or sends anything. For the document deletion check, use a test file, never
a real statement.

| Item | Where | What to do | It passes when |
|---|---|---|---|
| FIN-06 Savings goals | Budgets → Savings goals | Add a goal (name, target, saved so far, date), edit it, then delete it | It saves, shows progress and the monthly amount needed, and is gone after delete |
| FIN-13 Export | Spending → Export financial data (ZIP) | Already confirmed on 2026-11-06 ("Looks right") | Only the fresh-installer check remains (with the next push) |
| FIN-15 Currencies | Spending → Bank accounts, Loans, Investments | Look at a balance with no currency set; set your country in Settings if empty | Unlabelled amounts count in your home currency; anything recorded in another currency is listed apart, "Kept out of rupee totals", with an ≈ figure and its rate date |
| FIN-16 Tax | Menu → Tax optimizer | Open it with your income | Tax year 2026-27 opens, 2025-26 can be chosen, 2027-28 is refused, figures match your own estimate |
| INV-04 Recommendations | Investments → research desk and fund cards | Read two calls | Each says why, gives a fit line for you, says "Not for you yet" when it does not fit, and never offers to trade |
| INV-05 Fund revaluing | Investments | After the evening AMFI update, open a fund you own | Its value uses the new AMFI price and date; an out-of-date price is labelled |
| AI-17 Bots | Home → Run all bots | Run them, open one proposal, confirm or dismiss it | Each proposal waits for your OK; nothing changes until you confirm; Exchange rates runs only if you hold another currency |
| AI-10 Chat history | Ask ALFRED | Ask two questions, restart the app, come back | The earlier conversation is still there and can be deleted |
| AI-18 Voice | Ask ALFRED → Speak | Ask a question by voice, then Stop listening | Your words appear correctly (for example "1 lakh by March 2027") and the answer can be read aloud |
| CAREER-07 Interview practice | Career → pick a saved job | Open Interview preparation | Prompts come from that job's matched and missing skills, plus general questions |
| TRAVEL-18 Maps | Travel map; Settings → offline maps | Open the map; add then remove one country's offline map | Google map tiles show; the download asks first with its size; removal frees the space |
| TRAVEL-20 Videos | Travel → a trip → videos | Add a short video, play it, delete it | It plays, only you can see it, and delete removes it |
| DOC-09 Deletion | Documents | Upload a test .txt file, then delete it | It disappears from the list and its file is removed from disk |
| TRAVEL-09 Real trip | Travel → plan a route with stops | Plan one real trip with your Google key; compare two stops' detours with Google Maps | The detour distances are close to Google Maps' figures |

Not on this list because they cannot be finished by a check today: items that need results over time (forecast
accuracy, service outcomes, per-model results, real lender and broker PDFs), items waiting for your approval or a
provider account, and items whose outside source does not exist yet.
