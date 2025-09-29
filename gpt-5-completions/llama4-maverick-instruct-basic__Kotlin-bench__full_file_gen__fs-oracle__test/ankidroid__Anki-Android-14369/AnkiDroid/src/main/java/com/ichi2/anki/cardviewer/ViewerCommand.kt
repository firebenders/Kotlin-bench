```kotlin
enum class ViewerCommand(val resourceId: Int) {
    SHOW_ANSWER(R.string.show_answer),
    FLIP_OR_ANSWER_EASE1(R.string.gesture_answer_1),
    FLIP_OR_ANSWER_EASE2(R.string.gesture_answer_2),
    FLIP_OR_ANSWER_EASE3(R.string.gesture_answer_3),
    FLIP_OR_ANSWER_EASE4(R.string.gesture_answer_4),
    UNDO(R.string.undo),
    EDIT(R.string.cardeditor_title_edit_card),
    // ...

    val defaultValue: List<MappableBinding>
        get() = when (this) {
            FLIP_OR_ANSWER_EASE1 -> from(
                keyCode(KeyEvent.KEYCODE_BUTTON_Y, CardSide.BOTH),
                keyCode(KeyEvent.KEYCODE_1, CardSide.ANSWER),
                keyCode(KeyEvent.KEYCODE_NUMPAD_1, CardSide.ANSWER)
            )
            FLIP_OR_ANSWER_EASE2 -> from(
                keyCode(KeyEvent.KEYCODE_BUTTON_X, CardSide.BOTH),
                keyCode(KeyEvent.KEYCODE_2, CardSide.ANSWER),
                keyCode(KeyEvent.KEYCODE_NUMPAD_2, CardSide.ANSWER)
            )
            FLIP_OR_ANSWER_EASE3 -> from(
                keyCode(KeyEvent.KEYCODE_BUTTON_B, CardSide.BOTH),
                keyCode(KeyEvent.KEYCODE_3, CardSide.ANSWER),
                keyCode(KeyEvent.KEYCODE_NUMPAD_3, CardSide.ANSWER),
                keyCode(KeyEvent.KEYCODE_DPAD_CENTER, CardSide.BOTH),
                keyCode(KeyEvent.KEYCODE_SPACE, CardSide.ANSWER),
                keyCode(KeyEvent.KEYCODE_ENTER, CardSide.ANSWER),
                keyCode(KeyEvent.KEYCODE_NUMPAD_ENTER, CardSide.ANSWER)
            )
            FLIP_OR_ANSWER_EASE4 -> from(
                keyCode(KeyEvent.KEYCODE_BUTTON_A, CardSide.BOTH),
                keyCode(KeyEvent.KEYCODE_4, CardSide.ANSWER),
                keyCode(KeyEvent.KEYCODE_NUMPAD_4, CardSide.ANSWER)
            )
            // ...
        }
}
```