"""
Interactive exercise handlers: listing exercises for a unit, running a
listening-comprehension flow with an FSM (listening -> answering questions
-> showing the result), and revealing transcript/translation afterwards.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import bot, db
from keyboards import get_back_to_main_keyboard
from states import ExerciseState

router = Router()
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _get_questions(exercise: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Safely extract the list of questions from an exercise dict.

    `exercise['questions']` is already JSON-decoded by the database layer,
    but we defensively guard against it being missing or malformed.
    """
    questions = exercise.get("questions")
    if isinstance(questions, list):
        return questions
    logger.warning(
        f"Exercise {exercise.get('id')} has missing/malformed 'questions' field."
    )
    return []


async def _get_saved_score(
    user_id: int, exercise_id: int
) -> Optional[Tuple[int, int]]:
    """Look up a user's previously saved (score, total) for an exercise."""
    progress = await db.get_user_progress(user_id)
    for record in progress.get("records", []):
        if record.get("exercise_id") == exercise_id:
            return record["score"], record["total_questions"]
    return None


async def show_question(
    callback: CallbackQuery, state: FSMContext, exercise_id: int
) -> None:
    """
    Show the current question of an exercise.

    The previous message (either the "شروع سوالات" prompt or the
    "سوال بعدی" follow-up) is deleted and the question is sent as a fresh
    message, since editing a message that may have been a voice caption is
    unreliable.
    """
    try:
        exercise = await db.get_exercise(exercise_id)
        if not exercise:
            await callback.message.answer("⚠️ تمرین یافت نشد.")
            await state.clear()
            return

        questions = _get_questions(exercise)
        if not questions:
            await callback.message.answer(
                "⚠️ سوالات این تمرین به درستی ثبت نشده‌اند.",
                reply_markup=get_back_to_main_keyboard(),
            )
            await state.clear()
            return

        data = await state.get_data()
        current_question = data.get("current_question", 0)

        if current_question >= len(questions):
            # Defensive fallback: if we've somehow run past the last
            # question, jump straight to the result.
            await _send_result(callback, state, exercise_id)
            return

        question = questions[current_question]
        total = len(questions)

        text = (
            f"❓ سوال {current_question + 1} از {total}:\n"
            f"{question.get('question', '')}"
        )

        builder = InlineKeyboardBuilder()
        for idx, option in enumerate(question.get("options", [])):
            builder.row(
                InlineKeyboardButton(
                    text=option,
                    callback_data=f"answer:{exercise_id}:{current_question}:{idx}",
                )
            )

        try:
            await callback.message.delete()
        except Exception:
            # Message may already be gone (e.g. deleted manually) - ignore.
            pass

        await bot.send_message(
            callback.message.chat.id, text, reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Error showing question for exercise {exercise_id}: {e}")


async def _send_result(
    callback: CallbackQuery, state: FSMContext, exercise_id: int
) -> None:
    """Save progress and send the final result message, then clear state."""
    data = await state.get_data()
    score = data.get("score", 0)

    exercise = await db.get_exercise(exercise_id)
    questions = _get_questions(exercise) if exercise else []
    total = len(questions)

    await db.save_user_progress(callback.from_user.id, exercise_id, score, total)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📄 نمایش Transcript",
            callback_data=f"show_ex_transcript:{exercise_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🇮🇷 نمایش ترجمه",
            callback_data=f"show_ex_translation:{exercise_id}",
        )
    )
    builder.row(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back:main"))

    await callback.message.answer(
        f"🎉 نتیجه تمرین\nشما {score} از {total} سوال را درست پاسخ دادید!",
        reply_markup=builder.as_markup(),
    )

    await state.clear()


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------

@router.callback_query(F.data.startswith("unit_exercises:"))
async def handle_unit_exercises(callback: CallbackQuery) -> None:
    """List all exercises for a given level/unit/source."""
    try:
        _, level, unit_num, source = callback.data.split(":")
        unit = int(unit_num)

        exercises = await db.get_exercises_by_level_unit(level, unit, source)

        if not exercises:
            await callback.message.edit_text(
                "هنوز تمرینی برای این بخش وجود ندارد.",
                reply_markup=get_back_to_main_keyboard(),
            )
            await callback.answer()
            return

        builder = InlineKeyboardBuilder()
        for ex in exercises:
            builder.row(
                InlineKeyboardButton(
                    text=ex["title"], callback_data=f"start_exercise:{ex['id']}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"level_menu:{level}")
        )

        await callback.message.edit_text(
            "📝 لیست تمرینات:", reply_markup=builder.as_markup()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error listing unit exercises '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("start_exercise:"))
async def handle_start_exercise(callback: CallbackQuery, state: FSMContext) -> None:
    """Start an exercise: play its audio (if any) and offer to begin questions."""
    try:
        exercise_id = int(callback.data.split(":")[1])
        ex = await db.get_exercise(exercise_id)

        if not ex:
            await callback.answer("⚠️ تمرین یافت نشد.", show_alert=True)
            return

        if ex.get("audio_file_id"):
            await bot.send_audio(
                chat_id=callback.message.chat.id,
                audio=ex["audio_file_id"],
                title=ex.get("title", "Exercise"),
            )

        await state.set_state(ExerciseState.listening)
        await state.update_data(exercise_id=exercise_id, score=0, current_question=0)

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="📝 شروع سوالات", callback_data=f"begin_questions:{exercise_id}"
            )
        )

        await callback.message.answer(
            "🎧 به مکالمه گوش بده و به سوالات پاسخ بده.\nوقتی آماده بودی، دکمه زیر را بزن:",
            reply_markup=builder.as_markup(),
        )

        await callback.answer()
    except Exception as e:
        logger.error(f"Error starting exercise '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("begin_questions:"))
async def handle_begin_questions(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch to the answering state and show the first question."""
    try:
        exercise_id = int(callback.data.split(":")[1])
        await state.set_state(ExerciseState.answering)
        await show_question(callback, state, exercise_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error beginning questions '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("answer:"))
async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    """Grade the selected answer, show feedback, and offer the next step."""
    try:
        _, exercise_id_raw, q_index_raw, opt_index_raw = callback.data.split(":")
        exercise_id = int(exercise_id_raw)
        q_index = int(q_index_raw)
        opt_index = int(opt_index_raw)

        exercise = await db.get_exercise(exercise_id)
        if not exercise:
            await callback.answer("⚠️ تمرین یافت نشد.", show_alert=True)
            return

        questions = _get_questions(exercise)
        if q_index >= len(questions):
            await callback.answer("⚠️ این سوال دیگر معتبر نیست.", show_alert=True)
            return

        question = questions[q_index]
        options = question.get("options", [])
        correct_idx = question.get("correct")
        is_correct = opt_index == correct_idx

        # Build a feedback keyboard: mark the chosen option and, if wrong,
        # also mark the actually-correct option.
        builder = InlineKeyboardBuilder()
        for idx, option in enumerate(options):
            if idx == opt_index and is_correct:
                label = f"✅ {option}"
            elif idx == opt_index and not is_correct:
                label = f"❌ {option}"
            elif idx == correct_idx:
                label = f"✅ {option}"
            else:
                label = option
            builder.row(InlineKeyboardButton(text=label, callback_data="noop"))

        try:
            await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
        except Exception:
            pass

        data = await state.get_data()
        score = data.get("score", 0)
        if is_correct:
            score += 1
        await state.update_data(score=score)

        is_last_question = q_index >= len(questions) - 1
        next_builder = InlineKeyboardBuilder()
        if is_last_question:
            next_builder.row(
                InlineKeyboardButton(
                    text="📊 مشاهده نتیجه",
                    callback_data=f"show_result:{exercise_id}",
                )
            )
        else:
            next_builder.row(
                InlineKeyboardButton(
                    text="➡️ سوال بعدی",
                    callback_data=f"next_question:{exercise_id}",
                )
            )

        feedback_text = "✅ درست بود!" if is_correct else "❌ اشتباه بود."
        await callback.message.answer(
            feedback_text, reply_markup=next_builder.as_markup()
        )

        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling answer '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    """Swallow taps on already-answered feedback buttons."""
    await callback.answer()


@router.callback_query(F.data.startswith("next_question:"))
async def handle_next_question(callback: CallbackQuery, state: FSMContext) -> None:
    """Advance to the next question and display it."""
    try:
        exercise_id = int(callback.data.split(":")[1])
        data = await state.get_data()
        current_question = data.get("current_question", 0) + 1
        await state.update_data(current_question=current_question)
        await show_question(callback, state, exercise_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error advancing to next question '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("show_result:"))
async def handle_show_result(callback: CallbackQuery, state: FSMContext) -> None:
    """Finalize the exercise: save the score and show the result screen."""
    try:
        exercise_id = int(callback.data.split(":")[1])
        await _send_result(callback, state, exercise_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error showing result '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("show_ex_transcript:"))
async def handle_show_exercise_transcript(callback: CallbackQuery) -> None:
    """Show the transcript of a completed exercise."""
    try:
        exercise_id = int(callback.data.split(":")[1])
        exercise = await db.get_exercise(exercise_id)

        if not exercise:
            await callback.answer("⚠️ تمرین یافت نشد.", show_alert=True)
            return

        transcript = exercise.get("transcript")
        text = (
            f"📄 Transcript:\n\n{transcript}"
            if transcript
            else "📄 متأسفانه transcript برای این تمرین ثبت نشده است."
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔙 بازگشت به نتیجه",
                callback_data=f"view_result:{exercise_id}",
            )
        )

        await callback.message.answer(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Error showing exercise transcript '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("show_ex_translation:"))
async def handle_show_exercise_translation(callback: CallbackQuery) -> None:
    """Show the translation of a completed exercise."""
    try:
        exercise_id = int(callback.data.split(":")[1])
        exercise = await db.get_exercise(exercise_id)

        if not exercise:
            await callback.answer("⚠️ تمرین یافت نشد.", show_alert=True)
            return

        translation = exercise.get("translation")
        text = (
            f"🇮🇷 ترجمه:\n\n{translation}"
            if translation
            else "🇮🇷 متأسفانه ترجمه‌ای برای این تمرین ثبت نشده است."
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔙 بازگشت به نتیجه",
                callback_data=f"view_result:{exercise_id}",
            )
        )

        await callback.message.answer(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Error showing exercise translation '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("view_result:"))
async def handle_view_result(callback: CallbackQuery) -> None:
    """
    Re-display a previously saved result.

    Used by the transcript/translation screens' "back to result" button,
    after the exercise's FSM state has already been cleared - the score is
    read back from the database instead.
    """
    try:
        exercise_id = int(callback.data.split(":")[1])
        saved = await _get_saved_score(callback.from_user.id, exercise_id)

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="📄 نمایش Transcript",
                callback_data=f"show_ex_transcript:{exercise_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🇮🇷 نمایش ترجمه",
                callback_data=f"show_ex_translation:{exercise_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back:main")
        )

        if saved:
            score, total = saved
            text = f"🎉 نتیجه تمرین\nشما {score} از {total} سوال را درست پاسخ دادید!"
        else:
            text = "⚠️ نتیجه‌ای برای این تمرین ثبت نشده است."

        await callback.message.answer(text, reply_markup=builder.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"Error viewing result '{callback.data}': {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)
