```kotlin
    SHOW_ALL_HINTS(R.string.gesture_show_all_hints),
    ADD_NOTE(R.string.menu_add_note),
    RESCHEDULE_CARD(R.string.reschedule_card);

    companion object {
        val allDefaultBindings: List<MappableBinding>
            get() = Arrays.stream(values())
                .flatMap { x: ViewerCommand -> x.defaultValue.stream() }
                .collect(Collectors.toList())
    }

    // ...

    val defaultValue: List<MappableBinding>
        get() = // If we use the serialised format, then this adds additional coupling to the properties.
            when (this) {
                // ...
                SHOW_ALL_HINTS -> from(keyCode(KeyEvent.KEYCODE_G, CardSide.BOTH))
                ADD_NOTE -> from(keyCode(KeyEvent.KEYCODE_A, CardSide.BOTH))
                RESCHEDULE_CARD -> from(unicode('R', CardSide.BOTH, shift()))
                else -> ArrayList()
            }
}
```