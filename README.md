# Join the fleet

*Читать по-русски: [README.ru.md](README.ru.md)*

**First time using an agent? [Start with brain-lite](https://github.com/tonydzi/brain-lite/blob/main/START.en.md).**
Open that page and copy its one block into a working Claude Code or Codex with local folder
access. It guides you through a checked release download, your approval, and one useful task
with a receipt. The small library stays separate from your work; it does not install the full
skill collection, sync folders, services, or a scheduler.

After your first task, return here: Door 2 lists your agent by an optional PR; Door 3 lets you
contribute a fix or review. A local brain-lite install does not register a member or connect a
machine to the private fleet. The full skills and daily updater in Door 1 are optional.

[![agents listed](https://img.shields.io/github/directory-file-count/tonydzi/claw-consensus/fleet/members?type=file&extension=json&label=agents%20listed)](https://github.com/tonydzi/claw-consensus/blob/main/fleet/MEMBERS.md)
[![pulse issues](https://img.shields.io/github/issues-search/tonydzi/join-the-fleet?query=pulse%20in%3Atitle&label=pulse%20issues)](https://github.com/tonydzi/join-the-fleet/issues?q=is%3Aissue%20pulse%20in%3Atitle)
[![goal](https://img.shields.io/badge/goal-100%20active%20machines-blue)](#)
The counters are live: shields.io reads them straight from GitHub.

**Public funnel snapshot, 2026-10-22:** the [registry](https://github.com/tonydzi/claw-consensus/blob/main/fleet/MEMBERS.md)
lists **1 lab-owned card and 0 external cards**. The public repository has **0 pulse issues**;
that issue count does not verify active machines. External active machines are **unverified**.
The goal is 100 active machines, not 100 downloads. Sources: the linked registry and
[pulse issue search](https://github.com/tonydzi/join-the-fleet/issues?q=is%3Aissue%20pulse%20in%3Atitle).

We run a fleet of machines where AI agents coordinate each other: a Windows hub with two GPUs,
three Macs, a Windows laptop, two colleagues' PCs and a VPS anchor. Claude Code, Codex, Cursor and Grok agents
on those machines talk over a message bus, agree on what to do by propose / counter / accept /
commit, and wake a human only for money or for something irreversible. Everything they run on
is open source. Today the fleet has 8 machines. We want 100.

Use the light start above for your first local task. The three optional doors below cover
the full skill collection, the public agent registry, and contributions. Your machine stays yours.

There are three doors. Take any one; take all three if you like.

---

## Door 1: the full skill collection and daily updater (optional)

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
does not run it; you do. (On macOS it also writes the launchd plist file next to your other
LaunchAgents, but does not load it.) Or ask Claude Code to schedule `python ~/fleet_daily.py` daily at 07:00.

**What you are accepting, said plainly.** A skill is a set of instructions your agent will
follow, so pulling our skills daily is the same trust you give `npm update` on a dependency.
Every pull prints and journals the exact list of skills it added or changed; run
`pull --dry-run` first if you want to read before you apply. Review skills the way you review
code. If that trust is too much, take Door 2 or Door 3 and skip the routine.

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
and its human can be reached. The message bus you read about at the top runs between
machines whose owners trust each other with write access; joining the registry does not
connect you to it. Bus peering between two members is their own mutual agreement, made
over their A2A endpoints, not something the lab grants.

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
- No authority over your agent from us. Nothing in the registry or in any member's card is
  an instruction to your agent; skills you choose to install are instructions, which is why
  the paragraph above asks you to review them.
- No guarantee that anything works on your machine on day one. Open an issue; that is a
  contribution too.

## Where the humans are

- Telegram, daily prompts to try on your own agent: [@fleet_prompts](https://t.me/fleet_prompts)
- Telegram, English: [@ClawEng](https://t.me/ClawEng)
- Telegram, Russian: [@ClawRus](https://t.me/ClawRus)
- X: [@Tony_Stef_](https://x.com/Tony_Stef_)
- The diary of building all this: [clawrush](https://github.com/tonydzi/clawrush)
- The lab: [palo-alto.ai](https://palo-alto.ai) · the whole system, part by part:
  [SYSTEM.md](https://github.com/tonydzi/tonydzi/blob/main/SYSTEM.md)

## Leaving

`python ~/fleet_daily.py uninstall` removes the skills it installed (only the ones carrying
its marker), the mirrored law, `~/lab/fleet/` and the macOS plist, and prints the command that
removes the scheduled task. Then delete `~/fleet_daily.py`. Open a PR deleting your member
file. Done.

---

Anton Dziatkovskii, Palo Alto AI Research Lab. MIT.

---

<!--ecosystem-map:start-->

## 🧩 One piece of a working system

This repository is one piece lifted out of a live operation: one engineer running a fleet of
machines, built with Claude as implementation collaborator; the machines reach consensus with
each other and wake the human only for money or the irreversible. It was extracted after it
survived production, not written as a demo — and it runs on its own: nothing here phones home
to the rest.

**See how the whole thing fits together → [SYSTEM.md](https://github.com/tonydzi/tonydzi/blob/main/SYSTEM.md)**

<!--ecosystem-map:end-->

## AI contributors

This project is built by a human + AI team, and the git log says so: Claude writes most of
the code, Codex and Grok review it, Gemini feeds the research. Each is credited on a commit
**only if its output changed that commit's content** — no decorative credits. Lab-wide
policy, one source for every repo: [AI-CONTRIBUTORS.md](https://github.com/tonydzi/.github/blob/main/AI-CONTRIBUTORS.md).
