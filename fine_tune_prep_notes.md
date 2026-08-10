Fine-Tuning Preparation Notes — Day 14

Recurring issues from Day 13

1. Inconsistent or malformed final responses

Day 13 sometimes returned malformed tool-call-style output instead of a clean natural-language answer.

Fine-tuning can help: consistent response style, formatting, empathy, terminology, and disclaimer behavior.

Fine-tuning cannot fix by itself: broken application/tool-loop logic or API protocol problems.

2. Incorrect tool arguments and repeated tool calls

The Day 13 run included unsupported arguments such as Procedure, claim_id on get_plan_details, procedure_id, procedure_costs, and pre_authorization, plus repeated calls.

Fine-tuning may help: preferred tool-use behavior when shown strong examples.

Engineering still required: correct schemas, argument validation, dispatcher logic, and loop limits.

3. The no-tool control question triggered a tool

"How do I file a claim?" was intended as the no-tool control but triggered get_claim_status.

Fine-tuning can help: learning when not to invoke tools.

Fine-tuning cannot create missing facts: filing instructions must come from retrieval/context or an authoritative source.

Fine-Tuning vs Retrieval

Issue

Fine-tuning

Retrieval / application

Empathetic, consistent tone

Good fit

Not primary fix

Consistent disclaimer usage

Good fit

Not primary fix

Plain-language insurance terminology

Good fit

Not primary fix

New plan facts

Not reliable

Required

Current claim status

Not reliable

Required

Missing filing instructions

Cannot create source facts

Required

Broken tool schema/dispatcher

No

Application code fix

Repeated tool calls

May help behavior

Loop/code controls also needed

Hallucinated plan facts

May improve discipline

Grounding is required

Dataset

Full curated set: 30 examples

Training set: 25 examples

Held-out test set: 5 examples

Format: JSONL with messages containing system, user, and assistant roles.

Held-out examples are excluded from training and reserved for Day 15.

Quality Bar

Examples emphasize accurate coverage communication, empathetic tone, disclaimers, insurance terminology, information gaps, claims, plan details, out-of-pocket estimates, and medical-advice boundaries.

This dataset is a preparation artifact. Day 15 should determine whether fine-tuning actually improves held-out behavior without reducing factual grounding.