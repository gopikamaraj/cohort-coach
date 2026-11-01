"""Pilot sheets as a LOCAL demo data source. Never on the hosted judge demo.

The answered sheets of two pilot classrooms (roll numbers only, no names) live in the git-ignored
folder data/pilot/ on one machine. This package reads the folder's manifest and answer file; the
routes only exist when PILOT_DEMO=1, the folder is there and the manifest carries a consent note.
Child-level answers exist only inside the ignored answer file and in the browser's memory.
"""
