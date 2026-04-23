+++
title = "Building a Second Brain with Obsidian, Zettelkasten, and an AI Agent"
date = 2026-04-21T00:00:00+05:30
draft = false
math = false
+++

I spend most of my time building things. CNCFlow, a side project blog, ML experiments, X threads. The problem is not a lack of output -- it is that none of it compounds. I finish a project, learn something real, and two months later I am re-deriving the same insight from scratch because it never got written down anywhere I would actually look again.

I have tried Notion. Tried Apple Notes. Tried dumping things in a text file. All of them eventually become a graveyard of notes I never revisit.

So I set up something different. This post is about the system -- what it is, why it works, and the one thing that makes it actually stick.

## The problem with most note-taking

Most people take notes the wrong way. They copy. They highlight. They summarize what they read. Then they file it somewhere and feel organized.

None of that is learning. None of it compounds.

When you copy a sentence from a textbook, you are transcribing, not thinking. The note exists but the understanding does not. Two weeks later the note is as foreign as the textbook was the first time.

The thing that actually builds knowledge is elaborative encoding -- restating an idea in your own words, connecting it to something you already understand. This is not a productivity tip. It is how memory works. You encode new information by hooking it into existing mental models. No hooks, no retention.

A second brain should force you to do that. Most setups do not.

## Two systems, one vault

The system I use is a hybrid of PARA and Zettelkasten. They solve different problems.

PARA (Projects, Areas, Resources, Archive) is for navigation. It answers "where do I put this?" and "where do I find that?" It is project-oriented, folder-based, practical. Good for builders.

Zettelkasten is for thinking. It answers "what do I actually know?" and "how does this connect to that?" It is idea-oriented, flat, link-based. Good for writers and researchers.

The mistake people make is picking one and ignoring the other. PARA without Zettelkasten gives you a well-organized filing cabinet you never think with. Zettelkasten without PARA gives you a beautiful graph of ideas with no place to track actual work.

The vault structure I landed on:

```
00-Inbox/          everything lands here first
Projects/          one subfolder per active project
Daily/             date-named daily notes
Notes/             Zettelkasten permanent notes (flat)
Learning/          STEM subjects, structured
Templates/         note templates
Archive/           completed projects, old notes
```

Projects and Daily are pure PARA. Notes is pure Zettelkasten. Learning is the interesting hybrid.

## The three note types that matter

Zettelkasten has three kinds of notes, and most explanations of the system spend too much time on the taxonomy and not enough on why the types are different.

**Fleeting notes** are raw captures. They live in 00-Inbox. They are temporary by design -- process them within a week or delete them. Zero friction at capture time. Do not organize, do not format, just dump it.

**Concept notes** live in Learning/. One concept per note, explained in your own words. Fixed structure: what it is in your words, the core intuition, a concrete example you can trace through, where you got confused, and how it connects to things you already know. That last field -- where you got confused -- is the most valuable part most people skip. Your confusions are where your understanding has gaps. Future you needs to know where those are.

**Permanent notes** live in Notes/. These are the ones that compound. One fully-formed idea per note, stated as a claim. Not a topic -- a claim.

BAD: `Eigenvalues`
GOOD: `Eigenvalues represent stretch magnitude along a transformation's invariant axes`

BAD: `CNCFlow GTM`
GOOD: `CAD users switch tools only when workflow pain exceeds switching cost`

The difference matters. A topic title is a filing label. A claim title is a thought. When you write it as a claim, you have to commit to believing something. That forces the thinking.

## The rule that makes everything work

Write in your own words only. No copy-pasting.

This sounds obvious. It is the hardest part. The temptation when reading a paper or watching a lecture is to quote the good parts, paste them into a note, and feel like you captured something. You did not. You moved text from one place to another.

A wrong note you wrote yourself is more valuable than a correct note you copied. When you write something wrong, you will notice the contradiction when you link it to something else. The note will tell you where your understanding broke. A copied note just sits there looking authoritative.

## Learning STEM in the vault

STEM is where this system earns its keep more than anywhere else.

The standard study loop -- read, highlight, review -- fails because it is passive. You are reading the author's thoughts, not building your own. By the third session you are highlighting things you highlighted before because nothing stuck.

The vault forces a different loop. After reading a section or watching a lecture, I write a Concept Note in Learning/{subject}/. Not a summary -- my understanding. If I cannot explain it in my own words, I do not understand it yet, and that is useful to know.

Then I ask: does this connect to anything in Notes/? Can I extract a permanent note -- a cross-domain insight?

Working through linear algebra:
- Concept Note in Learning/Math/Linear-Algebra/: eigenvalues
- Then in Notes/: `Eigenvalues are to matrix transformations what CAD constraints are to parametric models -- they identify the invariant structure`

That second note is mine. Nobody wrote it in a textbook. It is hooked into my mental model of CAD, which I think about constantly. I will not forget it.

This is the compounding effect the system is supposed to produce. Your STEM learning starts talking to your project work. The graph of connected notes becomes a map of your actual understanding, not a collection of things you have read.

## Wiring an AI agent into the vault

The last piece is automation. I use Hermes (my local AI agent) to read and write to the vault directly.

Before any research task, Hermes searches Notes/ and Learning/ for what I already know. This prevents re-deriving things and surfaces relevant context automatically. If I ask it to explain something I have already written a concept note on, it reads the note first and builds on my existing understanding rather than explaining from scratch.

After a learning session, Hermes writes structured Concept Notes to the right Learning/ subfolder and extracts candidate permanent notes to Notes/. I review and edit them -- the thinking is mine, but the structuring is automated.

For projects, Hermes appends decisions to the decisions log table in the relevant Project Note. Every non-obvious decision gets a row: what was decided, why. This sounds like overhead. It pays back immediately the first time you pick up a paused project and actually remember why you made the choices you did.

## What I skip

I do not write notes for things I can re-derive in five minutes. I do not write notes for things that are already in the code, the commit history, or the PR description. I do not write notes to feel productive.

The weekly review is Sunday, twenty minutes. Process Inbox, promote or delete every note, update status tags on Learning notes (seedling -- just captured, growing -- building understanding, evergreen -- solid and stable), write or update one permanent note. If the review takes longer than twenty minutes, the system is too complicated.

Delete freely. A cluttered vault is a dead vault. If a note has not been touched in six months and is not evergreen, archive it or delete it.

## The real test

The system works if, six months from now, I can open the vault and quickly surface what I actually think about a topic -- not what I have read about it, but what I understand and how it connects to everything else I am working on.

The graph view in Obsidian will show clusters. Notes in the CS cluster linking to notes in the Projects cluster. An insight from linear algebra linking to a CNCFlow architecture decision. A note on organic growth on X linking to a note on network effects from graph theory.

Those links are the point. Not the notes themselves -- the connections between them. That is the second brain: not a better filing cabinet, but a map of how your own thinking connects.
