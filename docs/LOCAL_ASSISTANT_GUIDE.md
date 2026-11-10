# Using the local assistant

Under **Include local records**, choose the records to use for this question.
The permission note names the selected read-only data tool. Expand **Available
local read-only tools** to see the current catalogue. These tools read your own
Finance records, reviewed statement/document evidence, recorded Career application progress or saved Travel preferences;
they do not make changes, book travel, trade or contact external providers.
General chat keeps its existing verified-memory and conversation controls.

If a local source read cannot return validated evidence within its budget, your
question stays in the composer. Review or reload the source, then retry. Database
and file reads finish safely; ALFRED discards late results. External MCP servers
are not enabled by this catalogue. New actions still require their separate review
and confirmation flow.

![Local read-only tool permissions and a retained question on a synthetic account](images/usability/local-tools.png)

For application progress, choose **My recorded Career application progress**, then
ask "Summarize my application progress". You can also use **Review application
progress with ALFRED** on Career. The snapshot shows recorded stages and follow-up
dates, with scan limits and missing dates explained. **Open source records** returns
to Career to review or update them. Reopen and ask again to see changes.

Career snapshots stay on the page even when conversation history is enabled.
They work without a model and do not verify that an application or message was sent.
No salary, contacts, resume text or job-description text is included.

If Career shows **Follow-up dates need review**, inspect the affected opportunity's
recorded history. ALFRED leaves incomplete or conflicting dates unresolved and
pauses edits to that history. Other valid opportunities remain usable. The assistant
uses the same check. Refreshing or retrying does not replace the damaged history;
historical correction requires a separately reviewed recovery process.

![Recorded application progress on a synthetic account with history enabled and the Career snapshot kept page-only](images/usability/career-progress.png)

To create a savings goal, ask "add a savings goal Bike of 1000.25". To report
progress, ask "update Bike saved to 250.10". Review the name, amount and date in
the proposal, then choose **Confirm** or **Cancel**. Proposals expire after ten
minutes. If you change the goal elsewhere, ask again to obtain a fresh review.
Cancelled or expired cards cannot change a goal. These actions use the existing
Budgets validation locally and do not require a model or a paid API.

If confirmation is interrupted, retry the **same card** or check **Budgets**.
The same proposal can save only once, including after ALFRED restarts. A repeated
confirmation returns its receipt without overwriting subsequent changes. Reloading
the page clears the visible card; saved goals remain in Budgets. The local action
audit retains a keyed fingerprint and outcome, without the request, goal name or
amount. Clearing that audit makes its old proposals unavailable.

![Savings-goal review with synthetic values and an expiring Confirm card](images/usability/confirmed-action.png)

If local AI is unavailable, supported requests such as **Explain this record**
can still display current Finance, Loan, Investment, Budget or reviewed-statement
source cards. Select the owned record under **Include local records**, then ask.
ALFRED labels this as recorded evidence and supplies no model explanation or new
calculation. Open a citation to inspect verification, dates, currency and limitations.
Unsupported questions or changed evidence still require review; this recovery
does not enable cloud access or save a conversation turn.

![Current synthetic investment evidence recovered during a local adapter connection refusal](images/usability/offline-records.png)

Open **AI Assistant** from the sidebar. Under **Local answer style**, choose
Automatic, Concise, Detailed explanation, Comparison or Step by step. Enter your
question and press **Ask ALFRED**, or Ctrl+Enter. Automatic follows explicit
requests for brevity, detail, comparisons or steps. Answers have bounded lengths
and deadlines; detailed financial and document replies have a stricter limit.

Completed answers display headings, emphasis, inline code, fenced code blocks,
flat lists, quotes and simple pipe tables. Wide tables and code blocks can be
focused and scrolled with the keyboard. The same formatting appears when you
reopen a saved conversation; the original encrypted transcript is preserved.

Links, images and raw HTML supplied in answer text stay inert text. Verified source
links remain in the separate evidence cards. Questions and unverified streaming
previews remain plain text. Irregular or oversized tables fall back to text so
values are retained. Advanced Markdown and code syntax colouring are not supported.

![Formatted local comparison from a synthetic fictional prompt](images/usability/answer-format.png)

With private history off, local general-chat follow-ups can use up to three recent
turns from the current page. That dialogue stays in page memory. **New conversation**,
navigation or reload clears it. It is omitted when you choose cloud fallback;
private history remains a separate opt-in with retention and recovery controls.

![Local answer choices and conversation, using synthetic data](images/usability/local-answer-style.png)

Page-only local general chat streams an **unverified preview** while generating.
Press **Stop generation** to cancel, including by keyboard. Stop, timeout or a
broken connection preserves the draft and labels any preview **Partial, unverified**.
It has no source links, memory promotion or history-save controls. Use **Retry**
to request a complete answer. If the output limit is reached, choose Concise or
narrow the question. Partial or interrupted responses never enter saved history.

![Unverified preview and Stop generation, using synthetic data](images/usability/local-stream.png)

Figures and source-backed output are buffered until the complete response passes
validation. Source links and accepted answer controls appear only after validation.
Saved-history, domain and consented-fallback requests retain their complete-response
path in this slice; they have no streaming Stop control. History privacy and
financial grounding rules still apply.

If Ollama is unavailable, the draft remains in the composer. Open Settings →
Diagnostics to check local inference, then use **Retry**. External fallback still
requires its separate public-query consent; the answer-style selection controls
local generation.

Private conversation history requires both local operator authorization and your
explicit consent with a retention period. Open the private-history panel to enable
it when available. Saved conversations can be reopened after restarting ALFRED.
The assistant uses a bounded selection of recent general-chat turns for follow-up
questions. Reopened answers are labelled historical and their sources may be stale.

Inside the private-history panel, **Search saved titles on this page** filters
the saved conversation list as you type. It searches titles, without sending the
search text to a server or model. Clear the search to see the full owned list.
Reopen a conversation, edit its title and press **Save conversation title** (or
Enter in the title field). This keeps the transcript and original expiry. If
another window changed it, reopen the conversation before retrying; your unsent
question remains in the composer.

![Renamed conversation and local title search, using synthetic data](images/usability/conversation-history-controls.png)

Conversation statements remain unverified dialogue. Saving a conversation never
adds verified memory facts or changes your financial records. For document or
financial questions, select the owned source and inspect its evidence cards.
Unsupported numeric or currency claims are withheld from AI prose. Check missing
evidence rather than treating a longer answer as greater certainty.
