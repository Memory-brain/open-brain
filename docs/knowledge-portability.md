---
module: module-5-retrieval
related_skills:
  - open-brain-retrieve
last_updated: 2026-10-06
---

# Knowledge Portability: When Your Vault Is Stranded on Your Laptop

## The Problem

You've spent two years building a knowledge vault. It contains your best thinking on the topics that matter most to your work — frameworks you've tested, cases you've documented, insights you've distilled from hundreds of hours of reading and experience. This system is supposed to make you more capable. But right now, you're in a meeting, someone asks a question you know you've thought deeply about, and the vault is sitting on your laptop at home.

Knowledge portability is the gap between a knowledge system as it exists on a single device and the contexts in which you actually need knowledge. The gap is not small. Knowledge workers need information during conversations, on mobile devices, in real-time decisions, when using other tools — virtually never in precisely the controlled context of sitting at a desk with a specific application open. A system that is inaccessible in these moments is not a personal knowledge system; it's a personal archive that happens to be useful when you're already at your computer.

The portability problem also affects integration with AI assistants. If you use large language models to help you think, write, or decide, they have no access to your vault. They can only draw on their training data and what you paste into the conversation. The specific knowledge you've accumulated — which is more relevant to your actual work than any generic training corpus — is invisible to the systems you're trying to use it with.

---

## Why It Happens

### 1. Local filesystem dependency

The dominant personal knowledge management tools — Obsidian, Logseq, Notion desktop, and similar applications — store knowledge in local folders or proprietary databases tied to a specific device. This architecture is appropriate for the primary authoring experience. It becomes a constraint when you need read access from any other context.

The underlying data is static until you sync it, and syncing only solves the multi-device problem for the same application on different devices. It doesn't solve access from a browser, a mobile conversation, a terminal, or an AI assistant.

### 2. No queryable API layer

A knowledge vault structured as a folder of markdown files has no API. There is no endpoint you can call with a question and receive a structured answer. There is no authentication layer that lets another application say "I'm an authorized consumer of this knowledge." The vault is a filesystem artifact, not a service.

This architectural limitation means that every tool that could benefit from your knowledge — AI assistants, mobile apps, team collaboration tools — requires either copying the content manually or going without. Neither scales.

### 3. Monolithic architecture conflates authoring and retrieval

Most vault tools are designed for a single use case: a person sitting at a computer, authoring and reading notes. The authoring and retrieval experiences are inseparable — to query the vault, you open the application, which requires the application to be installed and the files to be present. There's no lightweight retrieval mode for when you just need to ask a question without opening the full authoring environment.

---

## How to Detect It

This is one of the easier failure modes to detect because the pain is concrete and immediate:

**The frequency test:** Over the past month, how many times did you need information from your vault but couldn't access it because you weren't at your computer? Even once a week represents a significant portability failure.

**The AI integration test:** When you use an AI assistant to help you think through a problem, can that assistant access your vault? If not, you're getting generic assistance when domain-specific assistance is available but unreachable.

**The meeting test:** In your last five significant meetings, were there moments when you could have contributed more — asked a better question, made a stronger argument, surfaced a relevant framework — if you'd had vault access? If yes, portability is costing you in real professional situations.

**The reconstruction test:** How often do you reconstruct, from scratch or from external sources, knowledge that you know is already in your vault? Every reconstruction is a portability cost — time spent re-finding or re-generating knowledge that could have been retrieved.

| Scenario | Vault accessible? | Portability level |
|---|---|---|
| At desk, primary computer, vault app open | Yes | Baseline |
| At desk, different browser tab | Depends on tool | Partial |
| On mobile device | Rarely | Poor |
| In AI assistant conversation | No (without integration) | None |
| On different computer | Requires sync + install | Limited |
| Offline | Local only | No remote |

---

## How to Fix It

No shipped Open Brain skill provides remote access. What follows is the pattern; the implementation is yours.

### Step 1: Separate the retrieval layer from the authoring layer

The authoring experience (creating, editing, organizing notes) can remain desktop-local. Retrieval does not need to be. Expose the vault through a small server that runs independently of the authoring application — the simplest form that works is a read-only MCP server over a copy of the vault's Markdown files.

Keep the server thin. It finds and returns notes; the assistant that calls it does the reasoning and synthesis. Everything that depends on the full local toolchain — intent routing, query expansion, the typed graph, myelination — stays on the machine where the vault lives.

### Step 2: Implement a minimal tool interface

A useful remote layer needs very few tools:

| Tool | Description |
|---|---|
| `search` | Keyword query → ranked notes with title, path and a snippet. Search is lexical: two to six terms work better than a long sentence. |
| `read` | Note path → full note content |
| `list` | Folder → the notes in it, so a client can orient itself |

Don't promise more than that. A natural-language "ask" endpoint or graph queries over HTTP sound attractive, but they move synthesis and graph logic onto the server, where they drift from the local versions. With search, read and list, any external context can reach vault knowledge without the full application.

### Step 3: Authenticate, and keep reads and writes apart

A vault exposed on the network needs authentication from day one:

- **Bearer token** on every request.
- **Separate write token.** If you add write tools (create a note, append to one), put them behind their own token. The read token should not merely be checked for write permission — it should not have it at all.
- **Writes land in an inbox, not the vault.** Remote captures go to a server-side inbox that you review and pull into the vault, so nothing written from a phone bypasses your normal processing.

### Step 4: Connect AI assistants to vault retrieval

Once the server exists, any MCP-capable assistant can query it during conversations. Instead of relying solely on training data, the assistant searches your vault when you ask a question in your domain, reads the relevant notes, and incorporates your specific knowledge into the response.

This transforms the AI assistant from a generic tool to one that has access to your specific thinking — the frameworks you trust, the cases you've documented, the principles you've built from experience.

### Step 5: Enable mobile access

Mobile access comes from the same server: an assistant app that supports remote MCP connectors reaches the vault from your phone, with no separate web frontend to build. If your client cannot send headers, use whatever auth it supports, and treat any credential it stores as a secret.

---

## Related

- [The Search Box Bottleneck: Why Text Search Fails Knowledge Vaults](search-box-bottleneck.md)
- [Multi-Modal Retrieval: Four Ways to Access What You Know](multi-modal-retrieval.md)
- [Isolated Retrieval: Finding Notes Without Following the Thread](isolated-retrieval.md)
