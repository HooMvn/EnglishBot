"""
FSM state groups used by the bot's interactive handlers.
"""

from aiogram.fsm.state import State, StatesGroup


class ExerciseState(StatesGroup):
    """States for interactive exercises (listening, answering, etc.)."""

    listening = State()
    answering = State()
    waiting_for_translation = State()
    waiting_for_summary = State()


class AdminState(StatesGroup):
    """States for admin-specific actions (if needed later)."""

    waiting_for_input = State()
