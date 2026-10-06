# Query Type 9 — Attempt first (JIT telling)

> Optional mode: the user writes their answer before seeing the retrieval and the skill reports the difference. Never in pure Operative mode. Read only when it is activated.

---

## Query Type 9: Attempt first (JIT telling)

Inverts the order of Query Types 1–8. Instead of answering first and letting the user read, it asks for their attempt first and answers by pointing out the difference — the retrieval version of *just-in-time telling*: giving the answer BEFORE someone has tried to work it out wastes the generative effort that produces real learning (diagnose the kind of gap before intervening; see the desirable-difficulties literature, e.g. Bjork). It complements Query Types 1–8, it does not replace them — activate it only when the user asks for it or when the context clearly suggests it (see below).

### When to activate

- The user asks explicitly: "let me try first", "what do I think the vault says before looking", "attempt first".
- The user is in the middle of writing a decision/PRD/post (Expressive or Critical mode) AND has not yet cited any PN — offer it once, without insisting if they decline: *"Want to write your answer in 2–3 lines before I show you what the vault says? It's optional — tell me if you'd rather I answer directly."*
- NEVER activate it in pure Operative mode (the user wants a specific fact quickly) or when they have already shown frustration/hurry in the session — the cost of the friction is only worth paying when there is cognitive time to generate.

### The move

1. Ask for the attempt: the user writes their answer in 2–3 lines (or less — do not demand length).
2. Run the normal retrieval (Query Types 1–8 as appropriate) WITHOUT showing anything yet.
3. Compare the user's attempt against the retrieved PNs/LNs. Report the difference, not a binary right/wrong verdict:
   - **Matches**: "your attempt and [[PN]] say the same thing — the PN adds [detail/evidence/nuance]."
   - **Diverges**: "your attempt says X, [[PN]] says Y — the difference is [exactly where]."
   - **Empty vault**: "there is nothing in the vault that confirms or contradicts your attempt — it is your hypothesis without backing yet, not an error."
4. Do NOT rephrase the user's attempt as if it were yours — quote it literally if you repeat it.
5. `times_retrieved` increments as in any retrieval — the prior attempt does not change the note's usage tracking.

### Logging

In the Retrieval Log (Step 10), add `intent: jit-telling` and a field `attempt: "<the user's literal attempt>"` before `outcome`. This is what makes it possible to measure later whether the mode actually improves retention vs normal Query Types — without the stored attempt there is nothing to compare against.

### What it does NOT do

- It does not replace any existing Query Type — it is an optional wrapper in front.
- It does not judge or score the quality of the user's attempt — it reports a difference, not a grade.
- It is not activated twice in a row in the same session if the user already declined once.

---
