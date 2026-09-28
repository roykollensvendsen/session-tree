# A five-minute user test of the viewer

The people who build a page are the worst judges of it. They know where
everything is. This is a short test where someone else uses the viewer
against the demo sessions while you watch. It is not a check that anything
works; the automatic tests do that. It finds where a newcomer hesitates,
looks in the wrong place or reads something wrongly.

Run it before a release, and after a change to how the page is laid out.

## Before the test

The demo is seven made-up sessions, such as a birthday party and a house
move, served by the viewer's own server. It needs no real sessions and no
account.

### What you need

- A Linux or macOS machine with `git`, `bash` and Python 3.11 or newer. The
  server uses only Python's standard library, so there is nothing to install.
- For a test on a phone: a network the phone and the machine share. That is
  either a [Tailscale](https://tailscale.com) tailnet with both on it, or the
  same Wi-Fi. The server has no password, but the demo holds nothing private.

### Start the demo

Start it at most ten minutes before the tester begins. The demo ages like real
sessions do, and after fifteen minutes a working session reads as stalled, so
the answers below stop being true. Start it again for each tester.

On this machine only, for a test on the machine's own screen:

<!-- not run: clones a repository and starts a server in the foreground -->
```bash
git clone https://github.com/roykollensvendsen/session-tree.git
cd session-tree
scripts/demo-viewer
```

Then open <http://127.0.0.1:8798/>.

For a phone, the server has to listen on an address the phone can reach. Find
it with `tailscale ip -4` on a tailnet, or `hostname -I` (Linux) or
`ipconfig getifaddr en0` (macOS) on Wi-Fi, and start the demo on it:

<!-- not run: starts a server in the foreground -->
```bash
SESSION_TREE_HOST=<that address> scripts/demo-viewer
```

The phone then opens `http://<that address>:8798/`. If the page does not load,
a firewall on the machine is the usual cause: port 8798 has to be open.

### Check it before the tester arrives

The page should show seven sessions, with **book club** first and a line at
the top saying questions are waiting. If **birthday party** says `står stille`,
the demo is too old: stop it with Ctrl-C and start it again.

Let the tester choose a phone or a computer, whichever they would use, and
have the observer sheet below ready, on paper or a copy.

## What to tell the tester

Read this aloud, and then say nothing more about the page:

> This page shows a few assistants that each work on a task for someone,
> such as planning a party. Each task is split into steps. I would like you
> to answer some questions using the page. Please think aloud: say what you
> look at and what you expect. You cannot do anything wrong; if something is
> hard, the page is at fault, not you. I will not help, so that I can see
> where it is unclear.

The page's labels are in Norwegian (`ledig`, `står stille`, `avvis`), and the
demo's tasks in English. If the tester does not read Norwegian, say so in the
notes, since it will colour tasks 2 and 7.

## The tasks

Read one at a time. Stop a task after about a minute and move on; being stuck
that long is the finding.

| # | Ask | What answers it | What it tests |
|---|---|---|---|
| 1 | Look at the page for five seconds, then look away. Which assistant needs something from you? | **book club**, which has questions waiting | Whether the page says who needs you at a glance |
| 2 | Is anything stuck? Where? | **street clean-up**: "Gloves and bags are bought" has stood still, and "The skip is delivered" was started before what it waits on was done | Whether stalled and blocked are seen, and told apart |
| 3 | In **birthday party**, what is being worked on now, and what could be started next? | "Every guest has an invitation" is being worked on. "The cake is ordered" is ready to start. "The room is decorated" waits on the invitations | Whether the arrows and states are read as order |
| 4 | Why was the clown dropped? | Its details say Maja is scared of clowns | That the struck-through task can be opened, and has details |
| 5 | Open the biggest plan on its own, and find what "The skip is collected" waits on | **street clean-up**, full screen: "The rubbish is in the skip" | The full-screen view and finding one task among eighty |
| 6 | In **birthday dinner**, is any helper working right now? | Yes, one, on "The shopping is done"; two others have finished | Whether the helpers' dots are read |
| 7 | One question asks about Thursday. It has already been answered elsewhere. Put it away | The question list at the top, **⊘**, then confirm | The question list and putting a question away |
| 8 | Which assistant has stopped for good? | **bike repair** | Whether an ended session looks ended |

## The observer sheet

For each task write:

- **Done:** alone, with a hint, or not done.
- **Time:** roughly, in seconds.
- **Where they looked first**, and anything they read wrongly.
- **What they said**, in their words.

Then ask:

1. What was the hardest thing to find?
2. What did you think a colour or a symbol meant that turned out to mean
   something else?
3. Would you know, from this page alone, when an assistant needs you?

## After the test

Write what happened as `docs/user-tests/<date>.md`, with the tester described
only by how used to such tools they are, never by name. List each problem once,
worst first, with the task it came from. Then treat it like a design review
(`.claude/skills/design-review/SKILL.md`): the user of the viewer decides what
to fix, and each fix goes through `.claude/skills/ship-change/SKILL.md`.

Where a problem can be measured, add the test that would have caught it, so
the next user test does not have to find it again.
