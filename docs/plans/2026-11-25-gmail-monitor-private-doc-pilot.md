# Canadian Gemini tailoring pilot

Status: **Unverified.** The following runbook uses fictional data. No live
account, email, or document was accessed to prepare it.

Test whether a Canadian personal Google account with AI Pro can process an
Aergia request through a Gmail monitor and return the draft in a private
Google Doc. The user should be able to start in Aergia and wait there, using
the same tailoring skill as the other agent hosts.

Google documents Gmail monitors for AI Pro and Ultra in Canada. Gemini Tasks
can use skills and work with Google Docs. Google requires confirmation for
changes to shared documents. Use docs owned by the test account with access
restricted to that account, and verify the actual behavior before offering
automatic tailoring. See the [Canadian schedules guide][schedules] and
[Gemini tasks guide][tasks].

## Fictional test data

- Job: Operations Analyst at Alder Shore Analytics in Halifax. Required: SQL,
  Excel, and written reporting. Preferred: Python.
- Evidence: a SQL coursework project from 2024, a 2025 Excel dashboard for
  synthetic bookstore data, and weekly status reports for a 2025 class
  project. There is no evidence of Python, paid employment, or quantified
  business outcomes.

## Run the pilot

1. In a Canadian personal test account, install the shared tailoring skill
   and create a Gemini Task with a Gmail monitor for subjects beginning with
   `[Aergia Tailoring]`. Give the task access to Google Docs. Instruct it to
   process the phase and request ID in the designated Doc and return the
   matching output in that Doc.
2. Create a private Doc containing only the job and an initial phase marker.
   From the test Gmail account, send an email to itself with the matching
   subject, a unique request ID, and the private Doc link. Keep the job and
   candidate evidence out of the email. Verify that the monitor fires, uses
   the skill, and writes the ideal target without any candidate input or an
   extra click in Gemini.
3. After recording the ideal, add the fictional candidate evidence to the
   Doc and advance its phase. Send the next trigger for that phase. Verify
   that the task writes a complete, structured candidate carrying the correct
   request ID. It should foreground SQL, Excel, and reporting while avoiding
   unsupported claims, employers, and metrics.
4. Record request-to-trigger and trigger-to-write time for each phase. Repeat
   with a second request and send a message without the trigger prefix.
   Record missed or duplicate triggers, wrong-document writes, confirmation
   prompts, and structured-output failures.

The pilot passes when both phases complete in the designated document using
the shared skill and the original IDs, with no per-run confirmation or
content transfer by the user. Confirm that the observed timing is suitable
for Aergia's waiting screen. Record the results before enabling the Gemini
button. Aergia's current tailoring flow remains the default.

[schedules]: https://support.google.com/gemini/answer/17094710?hl=en-ca
[tasks]: https://support.google.com/gemini/answer/17094507
