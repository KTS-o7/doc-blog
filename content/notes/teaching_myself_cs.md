+++
title = "Teaching Myself CS: The Plan"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "A structured self-study plan for computer science fundamentals — algorithms, systems, databases, networks, and mathematics, with resources and a realistic timeline."
tags = ["learning", "computer-science", "study-plan", "self-improvement"]
+++

I've been building things with code for a while now, but there are gaps. Not the kind that show up in day-to-day work -- the kind that show up when you're reading a paper and hit a concept you sort of understand but can't really explain, or when you're debugging something deep in a system and realize you're guessing at the underlying mechanics.

The fix is obvious in theory: go back and learn the fundamentals properly. The hard part is doing it without spending two years on a degree or burning out on a curriculum that assumes you have nothing else going on.

I've been working through [teachyourselfcs.com](https://teachyourselfcs.com/) as my backbone. Here's the plan I've laid out for myself and why I structured it this way.

## The Curriculum

TYCS breaks CS into 9 subjects and gives you a primary book and video course for each. The order is a suggestion, not a law:

| Subject | Book |
|---------|------|
| Programming | SICP |
| Computer Architecture | CS:APP / Nand2Tetris |
| Algorithms & Data Structures | The Algorithm Design Manual (Skiena) |
| Math for CS | MIT 6.042J notes |
| Operating Systems | OSTEP |
| Computer Networking | Top-Down Approach |
| Databases | Readings in Database Systems |
| Languages & Compilers | Crafting Interpreters |
| Distributed Systems | DDIA + MIT 6.824 |

The book choices are deliberate. SICP isn't just a programming book -- it's a book about how to think computationally. OSTEP is genuinely readable in a way most OS textbooks aren't. DDIA is probably the most practically useful book on the list if you're building anything that handles data at scale.

The target is 100-200 hours per subject. That's not a sprint, it's a multi-year project. The goal isn't to finish -- it's to build genuine depth in each area, then keep revisiting.

## The Problem I Had to Solve First

Standard study advice -- "30 minutes every day" -- doesn't work for me. I have high activation energy to start anything. Once I'm in, momentum takes over and I'll go for hours. But that first 15 minutes of friction is real and it kills sessions before they begin.

So the plan is ignition-focused rather than sustainment-focused:

- Sessions start with a 15-minute minimum, not a 2-hour block. The bar to start is low. Once started, I usually continue past it.
- Entry point is whatever subject feels most alive right now, not necessarily the next one in sequence. The order matters less than actually engaging.
- Each subject has a concrete project attached -- something you build, not just something you read. The project gives momentum a direction.

The Newton iteration thing from the TYCS intro stuck with me: when you hit something you don't understand, go back to the start of the section and re-read. Each pass gets you further. Don't skip over confusion -- re-enter it.

## How I'm Ordering It

I'm starting with three subjects in parallel across the first phase rather than going strictly sequential:

**Programming (SICP)** -- Chapters 1-3, doing every exercise. The exercises are the learning. Reading without doing is just moving your eyes across text. I'm supplementing with Exercism problems when I want something more applied.

**Computer Architecture (CS:APP / Nand2Tetris)** -- Starting with Nand2Tetris projects 1-5 because they're hands-on in a way that makes the abstractions stick. Build an ALU, then a CPU, then an assembler. By the time you reach CS:APP, you've already built the thing the book describes.

**Distributed Systems (DDIA)** -- Running this in parallel because I'm already working in this space and the reading compounds immediately with real work. DDIA cover-to-cover, then 2-3 papers per week from the MIT DSG reading list. The project target is implementing a Raft consensus module.

Algorithms and Math for CS come after the first wave. The ML path runs alongside: Andrew Ng's ML course after Algorithms, fast.ai after OS and Networking.

## What I'm Not Doing

No video lectures unless I'm stuck. The TYCS authors are explicit that books are the primary medium and videos are optional supplements. I've defaulted to videos too many times in the past -- they feel productive but the retention without active practice is low.

No skipping exercises to "get through" material faster. The only way through SICP is through the exercises. Same with Nand2Tetris. The projects aren't extra credit, they're the point.

No treating this as interview prep. The goal is actual understanding. Some of it will be useful in interviews, but that's a side effect, not the frame.

I'll track hours per subject and update this post as I go.
