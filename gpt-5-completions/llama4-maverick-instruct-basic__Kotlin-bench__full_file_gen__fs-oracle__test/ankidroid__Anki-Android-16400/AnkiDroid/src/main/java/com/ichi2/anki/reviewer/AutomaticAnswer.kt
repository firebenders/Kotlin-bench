```kotlin
class AutomaticAnswer(
    // ...
) {
    // ...
    fun toggle() {
        settings.toggle()
    }
    // ...
}

class AutomaticAnswerSettings(
    // ...
) {
    // ...
    fun toggle() {
        useTimer = !useTimer
    }
    // ...
}
```