# Try the viewer: a ten-minute test

Thank you for helping. This page is all you need.

**session-tree** is a page that shows what AI coding assistants are working
on. Each assistant splits its work into steps and draws them as a small map. A
person glances at the page to see which assistant needs them, and what is stuck.

Its makers know where everything is on it, so they cannot see where a newcomer
gets lost. That is what you can show them. You will start a demo with made-up
assistants, such as one planning a birthday party, answer eight questions using
the page, and send back where it was hard. **If something is hard, the page is
at fault, not you.** That is exactly what the test is for.

It takes about ten minutes: two to start the demo, five for the questions, and
a few to write back.

## 1. Start the demo

You need a Linux or macOS computer with `git`, `bash` and Python 3.11 or newer.
Nothing else is installed. Paste this into a terminal:

<!-- not run: clones a repository and starts a server in the foreground -->
```bash
git clone https://github.com/roykollensvendsen/session-tree.git
cd session-tree
scripts/demo-viewer
```

Leave it running, and open <http://127.0.0.1:8798/> in a browser. You should
see seven assistants, with **book club** first.

**To use a phone instead,** the phone and the computer must share a network,
such as the same Wi-Fi. Find the computer's address with `hostname -I`
(Linux) or `ipconfig getifaddr en0` (macOS). Stop the demo with Ctrl-C and start
it on that address:

<!-- not run: starts a server in the foreground -->
```bash
SESSION_TREE_HOST=<that address> scripts/demo-viewer
```

Then open `http://<that address>:8798/` on the phone. If it does not load, a
firewall on the computer is the usual cause: port 8798 has to be open.

**Start the questions within ten minutes.** The demo ages like the real thing,
and after fifteen minutes it starts to look different from what the questions
expect. If you are late, stop it with Ctrl-C and start it again.

## 2. Answer the questions

Take them one at a time, in order. Give each about a minute at most, and move
on if you are stuck; being stuck is a useful answer. Do not look anything up
elsewhere, and do not read the answers at the bottom until you are done.

For each question, jot down:

- your answer;
- **how sure** you are, and roughly **how long** it took;
- **where you looked first**, and anything that confused you.

The page's own labels are in Norwegian, such as `ledig` and `står stille`. If
you do not read Norwegian, say so when you write back; that is worth knowing too.

1. Look at the page for **five seconds**, then look away. Which assistant needs
   something from you?
2. Is anything stuck? Where?
3. In **birthday party**, what is being worked on now, and what could be
   started next?
4. In **birthday party**, why was the clown dropped?
5. Open the biggest map on its own, and find what the step "The skip is
   collected" is waiting for.
6. In **birthday dinner**, is any helper working right now?
7. One question on the page asks about Thursday. Pretend it has been answered
   elsewhere, and put it away.
8. Which assistant has stopped for good?

Then three last ones:

- What was the hardest thing to find?
- Did a colour or a symbol turn out to mean something other than you thought?
- From this page alone, would you know when an assistant needs you?

Stop the demo with Ctrl-C when you are done. It leaves nothing behind but the
folder you cloned.

## 3. Send back what you found

[**Open a new report on GitHub**](https://github.com/roykollensvendsen/session-tree/issues/new?template=user-test.md).
It has a place for each answer. Say whether you used a phone or a computer. No
GitHub account? Reply to whoever sent you this link, with the same notes.

<details>
<summary><b>The answers.</b> Open only once you have written yours down.</summary>

1. **book club**: it has questions waiting for you.
2. Two steps in **street clean-up**. "Gloves and bags are bought" has stood
   still for a long time. "The skip is delivered" was started before the step
   it waits for was done.
3. "Every guest has an invitation" is being worked on. "The cake is ordered"
   could start now. "The room is decorated" waits for the invitations.
4. The clown step's details say Maja is scared of clowns.
5. "The rubbish is in the skip", in **street clean-up** opened on its own.
6. Yes, one, on "The shopping is done". Two others have finished.
7. The list of questions at the top, then **⊘** beside the question, and
   confirm.
8. **bike repair**.

</details>

## For whoever sends the link

This test was made to find where a newcomer gets lost, which no automatic
test here can. If you can sit beside the tester, do. Ask them to think aloud,
and say nothing that helps; where they hesitate is the finding. Otherwise
sending the link is enough.

Each report arrives as an issue labelled `user-test`. Gather the problems it
names, worst first, and treat them like a design review
(`.claude/skills/design-review/SKILL.md`). The viewer's owner decides what to
fix, and each fix goes through `.claude/skills/ship-change/SKILL.md`. Where a
problem can be measured, add the test that would have caught it.

The answers above come from `scripts/demo_fixture.py`. A change there can make
one wrong, and nothing checks them, so read them again after changing the demo.
