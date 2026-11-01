"""Paper Studio: the termly check papers, built by code from approved rules. No AI is used.

rules.py      the rule set (templates, bug functions, blueprints, strings) and its YAML form
generator.py  generate_paper and make_twin: seeded, reproducible, with a stable hash
verifier.py   an independent re-check of a paper; shares no code with the generator
render.py     the child's paper, the answer key and the layout map (WeasyPrint, A4)
store.py      the database tables, rule versions (two people), papers and their approval
"""
