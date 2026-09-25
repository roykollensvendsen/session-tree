# Every rule, turned off in turn

*Run 2026-09-25 by `python scripts/mutate.py --write
evidence/tests/rule-mutations.md`, which is how to repeat it. The script
restores every file it touched before it exits.*

Green on a first run proves nothing: a test that has never been red tests
nothing. Where a rule is written before its test, the test is run red first.
Where a rule already exists, this is the substitute. Each rule is disabled in
turn, by replacing its one line with something that can never hold, and the
suite is run. A rule whose removal breaks no test is a rule nothing protects.

**Result: 14 of 14 rules turned off the test that names them.** None survived.

| Rule turned off | Tests that went red | The test that names it | Did that one go red? |
|---|---|---|---|
| an abandoned task is kept not removed | 3 | `test_an_abandoned_task_is_kept_not_removed` | yes |
| a started node waiting on open work is blocked | 2 | `test_a_started_node_waiting_on_open_work_is_blocked` | yes |
| a silent started node goes stalled | 1 | `test_a_silent_started_node_goes_stalled` | yes |
| independent goals are separate graphs | 2 | `test_independent_goals_are_separate_graphs` | yes |
| harness noise is not mistaken for a prompt | 1 | `test_harness_noise_is_not_mistaken_for_a_prompt` | yes |
| a half written line is left for next time | 1 | `test_a_half_written_line_is_left_for_next_time` | yes |
| a truncated transcript is reread from the top | 1 | `test_a_truncated_transcript_is_reread_from_the_top` | yes |
| an answered question box is no longer waiting | 1 | `test_an_answered_question_box_is_no_longer_waiting` | yes |
| a finished node no longer asks | 1 | `test_a_finished_node_no_longer_asks` | yes |
| a needs input line counts only when the session is idle | 1 | `test_a_needs_input_line_counts_only_when_the_session_is_idle` | yes |
| a step is drawn with its parents goal | 5 | `test_a_step_is_drawn_with_its_parents_goal` | yes |
| a breakdown nothing outside uses is folded | 2 | `test_a_breakdown_nothing_outside_uses_is_folded` | yes |
| the worst step colours the breakdown | 1 | `test_the_worst_step_colours_the_breakdown` | yes |
| a dismissed question no longer waits | 2 | `test_a_dismissed_question_no_longer_waits` | yes |

## What this does not prove

That the rules are the right rules, or that a rule catches every case of what
it names. It proves each rule is load-bearing: switch it off and a named test
says so. The last column is why that is worth more than a count: a mutation can
break a test for an incidental reason, and a `NO` there fails this script even
though something went red. A new rule follows the order in `CONTRIBUTING.md`
instead, a failing test first, and is added to `scripts/mutations.toml`, which
`tests/test_rules_have_evidence.py` requires.
