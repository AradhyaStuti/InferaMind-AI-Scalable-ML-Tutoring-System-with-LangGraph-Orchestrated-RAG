# Why your RAG app should refuse questions

Every RAG demo I tried last year had the same trick. Ask it about its actual subject — *"what is gradient descent?"* — and it answered well, with citations. Ask it *"who won the 2022 World Cup?"* and it still returned five "Sources" attached to a non-answer. The retrieval pipeline had no concept of *this question doesn't belong here*. It just dutifully embedded the query, ran a top-K cosine search over whatever was in the index, and handed the result to an LLM that was told to answer using the given context.

So I built RouteLM around a different default. Before retrieval ever runs, a small classifier picks one of three paths: answer with sources, answer from the model's own knowledge, or refuse outright. This post is about why that's the right default, and how I proved it works with a 6-query baseline against plain RAG.

This isn't a post about training models. It's about a 50-line router that earns its keep.

---

## The problem with plain RAG

Three failure modes show up immediately when plain RAG meets real users.

**Off-topic questions get confident-sounding fake citations.** Cosine similarity has no zero. Every query gets a top-5 back. The LLM is told "answer using these sources" and obliges, even when the sources are about something completely different. A modern, well-aligned model like Claude or GPT-4 will often catch this and say *"the retrieved excerpts don't cover your question"* — but it still wastes the retrieval call, returns five irrelevant source citations that the UI dutifully renders as "Sources", and burns generation tokens explaining what it can't do. The user sees something that *looks* like a grounded answer at a glance.

**In-scope-but-not-in-corpus questions get refused too aggressively** — or worse, the LLM ignores the retrieved context and answers from its priors anyway, with no signal to the user that the citations are decorative.

**Multi-corpus deployments treat all corpora as one bag of chunks.** A question about LangGraph might pull noise from a finance dataset because the embedding-space neighborhood was crowded.

The default behaviour of a RAG pipeline is to answer everything as if it's on-topic. That's a UX bug, not a model bug.

---

## The router

Each "course" (corpus) declares a list of anchor phrases — phrases a student in that course would naturally use. The ML course has things like `supervised learning`, `gradient descent`, `regularization`. The GenAI course has `transformer`, `RAG`, `LangGraph`. At startup those anchors get embedded with `bge-m3`.

For each incoming question, the score is:

```python
score = max(cosine_sim(query_vec, anchor_vec) for anchor_vec in course.anchors)
```

Max over anchors, not the centroid. I started with the textbook centroid approach (mean of all anchor embeddings) and it collapsed as soon as I added a second corpus. The GenAI course has 31 anchors that span LLM internals, RAG theory, LangChain APIs, and production concerns — averaging them produces a centroid that lands in a meaningless midpoint of embedding space. Legitimate questions like *"what is RAG?"* scored 0.48 against that centroid, alongside totally off-topic questions at 0.50. There was no threshold that separated them.

Switching to `max` over anchors made the score distribution cleanly bimodal. *"What is RAG?"* matches the `RAG` anchor directly and scores 0.77. *"What is the capital of France?"* doesn't match any anchor and scores 0.43. Now you can pick a threshold.

The decision is two thresholds per course (in JSON, hot-swappable):

| score | path |
|---|---|
| `≥ course_threshold` | RAG over that course's chunks |
| `≥ general_threshold` | direct LLM answer with a "this isn't in my notes" preamble |
| `< general_threshold` | refuse |

Per-course because different corpora have different anchor sharpness. The ML course tolerates 0.60. The GenAI corpus needs 0.58 because its anchors span more ground. Globalizing the thresholds would force one corpus to compromise for the other.

The whole thing lives in a LangGraph `StateGraph` with one conditional edge after `classify`. The same compiled graph object handles all three paths — there's no `if/else` outside the router itself, and adding a fourth corpus is a JSON entry plus a re-embed.

---

## Proving it

The reason for the router was a claim. Worth checking the claim.

I wrote a small comparison harness: 10 queries — 4 on-topic spread across three corpora, 6 deliberately off-topic — through two paths against the same Groq model (`llama-3.3-70b-versatile`):

- **Plain RAG**: top-5 retrieval over the entire 350-chunk index, into the same RAG prompt
- **RouteLM**: full pipeline with the router

Headline numbers:

| Metric | Plain RAG | RouteLM |
|---|---|---|
| Off-topic queries that returned source citations | 6 / 6 | 0 / 6 |
| Off-topic queries that triggered an LLM call | 6 / 6 | 0 / 6 |
| Off-topic "leak rate" (>200 chars + citations) | 100% | 0% |
| On-topic queries answered substantively | 4 / 4 | 4 / 4 |
| Avg latency on off-topic queries | ~1.1 s | ~0.48 s |

So on the on-topic side, the two systems are tied. The whole win is on the off-topic side, and it's bigger than the headline suggests.

A couple of things from looking at the actual outputs.

The Groq model is well-aligned. It doesn't fully hallucinate — on every off-topic query, plain RAG produced something like *"the retrieved excerpts don't cover the 2022 World Cup, they appear to be about machine learning..."*. That's honest. But it's still 400–900 characters of LLM output explaining what the system can't do. RouteLM returns a single fixed 202-character refusal in <500ms with no LLM call at all.

Plain RAG always returns 5 source chunks, even on off-topic queries. The UI would render those as "Sources: 5 chunks" attached to a non-answer. That's the worst kind of leak — it *looks* like a grounded answer at a glance.

Plain RAG burns the retrieval call AND the LLM call on every off-topic query. Across the 6 off-topic queries that's ~3.6 seconds of wasted Groq inference and 30 wasted FAISS lookups. RouteLM short-circuits at the router.

If I'd run this against a less-aligned model — or one with a stricter "you must answer using the given context" prompt — the leak rate would have been worse for plain RAG, not better. The router is the cheapest place to catch this.

---

## Three takeaways

The default behaviour of a RAG pipeline is to answer everything. That's almost never what the user actually wants.

A small classifier in front of retrieval is the cheapest way to fix it. No fine-tuning, no re-architecting — a centroid (or in my case, a max-anchor scorer) plus two thresholds per corpus is enough to cleanly separate on-topic from off-topic for most queries.

Always validate the design choice with a baseline. Numbers beat intuition — and writing the comparison script took less time than this paragraph.

Code, the live demo, and the full eval results are in the [RouteLM repo](https://github.com/aradhya-stuti/routelm).
