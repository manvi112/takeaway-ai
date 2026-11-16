# Evaluation set

Five synthetic meetings. Each has `<name>.txt` and `<name>.expected.json`.
The transcripts were written with the answers in mind, so the labels are ground truth
by construction, not hand-labelled from real meetings. Say this in the main README.

## Labelling rules
An item IS expected when:
- someone commits in the first person ("I'll send the budget by Friday");
- a task is assigned and accepted ("Can you...?" then "Sure, I'll...");
- someone clearly says a task must be done but names nobody ("Someone should email the client") -> owner null.

An item is NOT expected when it is:
- an idea ("maybe we could...") or something deferred ("let's discuss later", "not this quarter");
- a status update or past event;
- a vague wish to meet ("let's catch up soon").

Dates: resolved against `meeting_date`; "today" = that date; "tomorrow", weekdays and
"next Wednesday" become real dates; vague ("soon", "next week") -> null.

`evidence` is a list of acceptable verbatim lines: the model may quote either the request
or the acceptance. The scorer matches an extracted item to an expected one when its
evidence (normalised) matches one of these lines.

## Borderline calls
- "We should investigate the performance issues soon" (standup_01): a group aspiration with no
  owner, no concrete task and a vague date. Decided NOT an action item (16 Nov), after the first
  runs showed the model consistently skipping it. Earlier runs were scored with this item
  included, so their totals are out of 27 instead of 26.
- Ideas for later: a separate "open items" list for aspirations like this, which could feed
  reminders.
