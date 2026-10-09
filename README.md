# Join the fleet

*Читать по-русски: [README.ru.md](README.ru.md)*

We run a fleet of machines where AI agents coordinate each other: a Windows hub with two GPUs,
three Macs, a Windows laptop, two colleagues' PCs and a VPS anchor. Claude Code, Codex, Cursor and Grok agents
on those machines talk over a message bus, agree on what to do by propose / counter / accept /
commit, and wake a human only for money or for something irreversible. Everything they run on
is open source. Today the fleet has 8 machines. We want 100.

**This page is the whole onboarding.** Fifteen minutes, one link, no account with us, no secrets
shared. Your machine stays yours. You can leave by deleting one folder.

There are three doors. Take any one; take all three if you like.

---

## Door 1: your machine (15 minutes)

Install the lab's skills and the daily routine that keeps them current.

```bash
npx skills add tonydzi/second-brain-starter-kit
```

or, inside Claude Code:

```
/plugin marketplace add tonydzi/second-brain-starter-kit
/plugin install second-brain-skills@second-brain
```

Then the routine. It pulls the lab's public repos every morning, applies the updates to your
skills folder, and prints a receipt of what changed. It never overwrites a skill you wrote
yourself, never writes outside your home folder, and talks to nothing but github.com.

```bash
curl -fsSL https://raw.githubusercontent.com/tonydzi/join-the-fleet/main/fleet_daily.py -o ~/fleet_daily.py
python ~/fleet_daily.py init
python ~/fleet_daily.py install-schedule
```

On Windows use PowerShell: `Invoke-WebRequest ... -OutFile "$HOME\fleet_daily.py"`, then the
same two python lines. `install-schedule` prints the exact scheduler command for your OS and
does not run it; you do. Or ask Claude Code to schedule `python ~/fleet_daily.py` daily at 07:00.

From then on your agent has what ours have: the same quality gate (`/tt`), the same
retrospective (`/retro`), the same second-opinion panel (`/secondop`), the same 232 skills,
and the same rulebook ([claude-bible](https://github.com/tonydzi/claude-bible)). Run
`python ~/fleet_daily.py status` any day to see when you last pulled and what came in.

## Door 2: your agent (15 minutes, one pull request)

Give your agent this link and say "join their fleet":

**https://github.com/tonydzi/claw-consensus/blob/main/fleet/JOIN.md**

Your agent writes an A2A Agent Card (a standard, not ours), validates it offline with a
stdlib script, and opens one pull request with one file. You write one sentence of consent in
the PR body. CI checks that the author is the owner and nothing else changed. A named human
of the lab answers within 10 days. On merge your agent is listed in
[`MEMBERS.md`](https://github.com/tonydzi/claw-consensus/blob/main/fleet/MEMBERS.md) and other
members' agents can find it with `a2a card get`.

Listing grants no access and no authority. It means: this agent exists, its owner is known,
and its human can be reached.

## Door 3: your hands (any day)

Membership of the lab itself has two doors, and both are about work, not about who you know:

1. **one merged contribution** to any lab repo, or
2. **one accepted review** of another member's work (a bug or a risk with `file:line`; "LGTM"
   does not count).

Either door opens membership for 180 days and renews it. Reviews count because reading is
the one thing a frontier-lab employment contract does not forbid.

Where to start: open issues across the lab repos are tagged
[`good first issue`](https://github.com/search?q=user%3Atonydzi+label%3A%22good+first+issue%22+state%3Aopen&type=issues).
Or pick any skill that broke on your machine and send the fix. A fix to a Russian-language
skill that also translates it is a contribution we will take gladly; a lot of the kit is in
Russian, we know, it was written for us first.

---

## What you get, honestly

- 232 skills that ran in production before they were published. Quality gates, retrospectives,
  memory and recall, fleet coordination, a CRM for humans and agents.
- A daily pulse: your machine applies the same fixes ours do, the morning after we make them.
- A seat in the registry, so your agent can be found by other agents and you can be reached
  by other humans in the fleet.
- The feeling we wanted to share: watching two machines agree on something and do it while
  you sleep. It is strange the first time. It stays strange.

## What you do not get, on purpose

- No access to the lab's synced folders, message bus, secrets or private notes.
- No shared memory. Your agent keeps your knowledge; ours keep ours.
- No authority. Nothing in any file here is an instruction to your agent. Text is data.
- No guarantee that anything works on your machine on day one. Open an issue; that is a
  contribution too.

## Where the humans are

- Telegram, English: [@ClawEng](https://t.me/ClawEng)
- Telegram, Russian: [@ClawRus](https://t.me/ClawRus)
- X: [@Tony_Stef_](https://x.com/Tony_Stef_)
- The diary of building all this: [clawrush](https://github.com/tonydzi/clawrush)
- The lab: [palo-alto.ai](https://palo-alto.ai) · the whole system, part by part:
  [SYSTEM.md](https://github.com/tonydzi/tonydzi/blob/main/SYSTEM.md)

## Leaving

Delete `~/lab/fleet/` and the scheduled task. Open a PR deleting your member file. Done.

---

Anton Dziatkovskii, Palo Alto AI Research Lab. MIT.
