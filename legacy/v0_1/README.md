# TAHU — v0.1 research prototype

Original experiment date: 2026-09-24. Status: a development demonstration, without real AI integration or independent validation. It is not suitable as a production security boundary. This archived guide was translated into English on 2026-10-25; the original prototype code and results remain unchanged.

## Principles and scope

TAHU explores restraint, stopping and corrigibility as inspectable engineering constraints. Its philosophical inspiration is a modern interpretation, not a quotation or evidence of security effectiveness.

| Letter | Principle | Implementation in this version |
|---|---|---|
| T | Traceability | Allow/deny reasons, operation counts and source-exposure labels for each attempt |
| A | Authorization | Tool allowlists, fixed destinations, information-flow restrictions and action budgets |
| H | Human Oversight | Trusted-operator stop interface and one-use approval bound to an artifact and destination |
| U | Uncertainty Awareness | Block sending records with unknown classification until classified |

Here, uncertainty awareness is a rule about unknown record classifications, not a measurement of model confidence or detection of all unknown risks. Human oversight is a code interface, not a finished authentication or review product.

## Research question

An agent's ability to read records, derive drafts and send messages does not authorize it to transfer restricted information to a public destination. TAHU v0.1 tracks sources across successive operations to investigate whether restrictions can survive rewriting and omitted provenance.

This version demonstrates information-flow constraints only. It does not address global AI governance, military risks, manipulation, employment effects, model deception or self-replication. Purpose constraints, semantic cumulative harm and comprehensive risk budgets are not implemented.

## Implementation and trust boundary

The caller submits structured `read`, `derive` and `send` requests. The monitor checks them before simulating operations in memory. It sends no actual messages, accesses no network and reads or writes no user business records.

A trusted host initializes the artifact registry and labels; agents do not self-report initial classifications. Derived artifacts inherit source labels. TAHU mode also retains restricted session-exposure labels so that an agent cannot read sensitive information and clear its restrictions by omitting sources. Artifact IDs cannot be overwritten. Public destinations accept public artifacts only; internal destinations can accept `restricted` artifacts, and `unknown` artifacts cannot be sent.

Agent requests cannot change labels, policy or budgets, or grant permission. The trusted operator can issue one-use approval bound to an artifact ID and destination. Approval cannot override stop state, budget limits or unknown classifications.

**This is not process isolation.** Python object fields are not tamper-resistant storage. Untrusted code in the same process with object references may modify fields or call trusted interfaces directly. Deployment requires a separate service protecting policy, credentials and state, authenticated separation of agents from operators, and mediation of every external execution path.

Other assumptions and gaps:

- Secrets in pretrained knowledge, existing context or other channels are outside this simulator; the initial environment needs separate constraints.
- Execution is sequential in one process, without concurrency safety, transactional persistence, crash recovery or state across restarts.
- Logs exist only in memory, are not tamper-resistant, and may contain sensitive request bodies. Deployment needs data minimization and access control.
- Session exposure only increases, which can block unrelated content. Agents cannot clear their own history.
- Fixed destinations are symbolic fixtures, without real URL/address normalization or destination authentication.
- Unknown-source handling depends on correct labels, not automatic discovery of all unknown sources.
- Action budgets count accepted operations, not total computation, network activity or rejected-request rates.
- Semantic manipulation, covert channels and encoding secrets through sequences of public choices are not detected.

## Reproduce

Python 3.10+ is required, with no third-party dependencies. From this archived directory:

```sh
python evaluate.py
```

The program prints a summary and regenerates `results.json`. All records are synthetic and contain no real personal information. Scenarios and implementation were developed together; this is not an independent security benchmark or a real-world success rate.

## Recorded results

Three modes use the same 17 development scenarios: 11 prohibited, five legitimate and one uncertain-source case. All modes share request validation, budgets and stop controls; information-flow checks differ.

| Mode | Prohibited scenarios blocked | Legitimate scenarios completed | Uncertain-source sending blocked | Expected outcomes overall |
|---|---:|---:|---:|---:|
| `tools`: tool and structural permissions | 5/11 | 5/5 | 0/1 | 10/17 |
| `lineage`: add explicit source-label inheritance | 9/11 | 5/5 | 1/1 | 15/17 |
| `tahu`: also retain session exposure | 11/11 | 4/5 | 1/1 | 16/17 |

Six additional control-property groups passed: one-use approval, destination binding, artifact binding, budget stop, operator stop, and denial without a send effect while retaining a reason.

**Retained counterexample:** after reading restricted information, a task that derives the unrelated text `2 + 2 = 4` is still denied public delivery. Session exposure closes the provenance-omission gap at a usability cost. Existing public artifacts that have not been rewritten can still be sent in this version.

The result establishes only that specified rules blocked prohibited actions in these authored scenarios, with one known false block. No real AI was called, no independent adversarial assessment was performed, and no superiority over mature information-flow systems or security benefit from philosophy itself was demonstrated.

## Originality and related work

Naming, inspiration and mechanisms require separate originality assessments. Source-label inheritance, information-flow control, least privilege and external oversight have substantial prior work. This version claims neither invention of these mechanisms nor global priority. Trademark and same-name project status have not been verified.

References identified for further reading and comparison:

- Robin R. Wang, [Can a Machine Flow Like Dao? The Daoist Philosophy on Artificial Intelligence](https://digitalcommons.lmu.edu/phil_fac/353/) (2021).
- Ruling Without Rulers: A Daoist Political Framework for AI Governance (2025), DOI: 10.23368/hyufcs.2025..14.006.
- [Constitutional AI: Harmlessness from AI Feedback](https://www.anthropic.com/news/constitutional-ai-harmlessness-from-ai-feedback).
- [NeMo Guardrails: A Toolkit for Controllable and Safe LLM Applications with Programmable Rails](https://arxiv.org/abs/2310.10501).
- [NIST AI Risk Management Framework](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10).

This list is not a comprehensive novelty search or an endorsement of TAHU.

## Historical v0.2 research plan

This section preserves the plan recorded with v0.1; consult the current documentation for subsequent implementation and evidence.

1. Compare dynamic information-flow control, taint tracking, agent-session isolation and capability authorization, allowing a conclusion of no new mechanism.
2. Investigate trusted-host context isolation between restricted and public tasks, with only approved inputs supplied to public tasks. Measure isolation cost and utility instead of relying on a model claiming to forget secrets.
3. Integrate a real model and compare baseline and TAHU with identical model, tools and tasks. Establish access and cost at implementation time; this prototype incurred no model-call charges.
4. Freeze the development set and add independently authored held-out cases covering omitted provenance, concurrency, restarts, approval reuse and prompt injection. Report variation across repeated runs rather than selecting the best result.
5. Predeclare unauthorized execution rate, legitimate completion, false blocks, latency and cost, with deployment-based targets fixed before observing results.
6. Publish failures and code for independent reproduction, and state research contributions only when differences and evidence support them.

This version is a research prototype and development experiment, not a validated general AI control system.
