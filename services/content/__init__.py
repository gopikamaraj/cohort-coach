"""Track content: definitions, the strategy library, templates, slots, versions, review, publish.

Content is data under `content/` (owned by Seema); this package loads it, validates it and moves
it through the two keys (the coach's approval, then the officer's activation). Nothing here calls
a model: call 5 lives in `ai/calls/` and hands its output to this package as a review item.
"""
