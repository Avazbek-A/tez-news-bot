"""Command handler modules, extracted from the monolithic bot.py.

This package is the first slice of breaking bot.py (~2,400 lines) into
cohesive, independently-testable command groups. Modules here depend only
on settings + translations + telegram types — never on bot.py — so there
is no import cycle. bot.py imports the handlers and registers them.
"""
