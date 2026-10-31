# Patterns slopscore does not score

slopscore matches phrases, sentence shapes, and Markdown block shapes. The patterns on this page
sit at the level of the whole document. They show up often in drafts that went through several
AI-assisted passes, and also in drafts nobody ran through a model. None of them can be checked
with a regex and a word list without flagging good writing too, so slopscore leaves them to a
human reader. This page is a checklist for that read, not an authorship test: finding these
patterns in a document says nothing about who wrote it.

Each entry gives the pattern, a short invented example, why slopscore does not score it, and how
to check for it by hand.

## Thesis restated in every section

**Example.** The summary says the program runs in four stages: detect, triage, fix, prevent.
Section 2 opens by naming the four stages again, section 3 closes on them, and the FAQ repeats
them.

**Why it is not scored.** Repeating a system's name or a key term in every section is correct
term consistency. The defect is restating the claim, which takes meaning to detect. slopscore
catches only the verbatim form: `REDUNDANT_REPEATED_SENTENCE` flags a sentence of 15 or more
words that recurs later with at most a word or two changed.

**How to check.** For each paragraph, ask what fact it adds that no other paragraph states. If
the answer is none, delete it. State the thesis once, in the summary.

## A wrap-up paragraph closing every section

**Example.** Each section ends on a paragraph that opens "This shows that..." or "Together,
these steps..." and carries no number, name, or date.

**Why it is not scored.** Some closers are worth keeping, and position alone does not separate
them. slopscore flags the most formulaic openers (`FORMULAIC_LESSON_FRAME`: "the larger lesson
is", "this case illustrates how", "taken together,"; `FORMULAIC_IN_CONCLUSION`) wherever they
appear, but it does not judge a section's last paragraph as such.

**How to check.** Read the last paragraph of each section on its own. If it restates the section
without a fact, end the section on the paragraph before it.

## Framing before evidence

**Example.** A results section opens with two paragraphs on why the approach matters before the
first measurement appears in paragraph three.

**Why it is not scored.** Some sections need context first. slopscore reports evidence density
(`genericity`, and runs of factless sentences in `metadiscourse`), but not where in a section the
first fact falls.

**How to check.** Find the first number, case, or named example in each section. If it is not in
the first two sentences, move it up.

## Claims larger than their support

**Example.** A heading promises a large dollar figure that the body never derives. A verb such as
"demonstrates" rests on a pilot of a few dozen units, most of which were not yet measurable.

**Why it is not scored.** Checking a derivation means following arithmetic and sources. A rule
such as "a figure in a heading must appear again in the body" would flag every document that
states a figure once.

**How to check.** For each headline number, point to the line that computes it and the source of
each input. Match the verb to the sample: "found" or "measured" for a pilot, "showed" for a
result that held, "demonstrated" only when the sample would survive review.

## Lists of abstract nouns

**Example.** "This reduces idle capacity, repair delays, and unnecessary cost." Five-item lists
of this kind in consecutive paragraphs.

**Why it is not scored.** Lists of three are ordinary English. slopscore's `parallelism`
dimension already treats rule-of-three as a weak tell that needs corroboration; scoring every
noun list would flag most technical writing.

**How to check.** Keep the item that matters most and give it a number. Cut the others or move
them to a table.

## One system, several names

**Example.** The same service is called by its project name, an acronym, and a descriptive phrase
in different sections.

**Why it is not scored.** Telling a synonym from a second system needs knowledge of the domain.

**How to check.** Search for each name. Pick one, define it at first use, and replace the rest.

## An ask buried in a modifier

**Example.** "This is an important area for continued investment" where the writer needs two
people for two quarters.

**Why it is not scored.** The request is implied. Nothing in the sentence marks it as an ask.

**How to check.** Have someone who did not write the document read only the summary and say what
is being asked, of whom, and by when. If they cannot, write the ask as a sentence with an owner
and a date.

## Present tense for something that does not exist yet

**Example.** "The service collects the logs, ranks the causes, and records the fix" in a document
whose plan section says the first version has not shipped.

**Why it is not scored.** Present tense is normal for describing a design. Only the rest of the
document shows whether the design has shipped.

**How to check.** For each capability described in the present tense, check whether it runs
today. If it does not, write "will" or "is designed to", and say which parts are manual today.

## Rebuttals of positions nobody took

**Example.** "Rather than building a separate service for each team, we extend the existing one"
when no reader proposed separate services.

**Why it is not scored.** The contrast is fine when someone did propose the alternative, and
only the reader knows whether they did. slopscore scores the most formulaic shapes of this move
("not merely X but Y", "it's not X, it's Y") in `parallelism`.

**How to check.** For each "rather than" or "instead of", name who proposed the alternative. If
nobody did, state what the design does and drop the contrast.

## Draft scaffolding

**Example.** TBD in a table column, a TODO in brackets, italic prompts left under headings, a
notes section marked for deletion.

**Why it is not scored.** People leave these in their own drafts, and they mark an unfinished
document, not a generated one. slopscore flags only unfilled template slots (`[X date]`, `[$X]`,
`[Company Name]`) under `RESIDUE_TEMPLATE_SLOT`, and assistant placeholders such as `[insert
date]` under `RESIDUE_PLACEHOLDER`.

**How to check.** Search for `TBD`, `TODO`, `[`, and italic lines before anyone else reads the
document. Track the unfinished parts in a separate list.
