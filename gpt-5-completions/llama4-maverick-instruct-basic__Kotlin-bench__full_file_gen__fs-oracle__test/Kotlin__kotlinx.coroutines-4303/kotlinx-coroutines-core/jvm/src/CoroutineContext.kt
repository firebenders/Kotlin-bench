```kotlin
// Used by withContext when context changes, but dispatcher stays the same
internal actual class UndispatchedCoroutine<in T>actual constructor (
    context: CoroutineContext,
    uCont: Continuation<T>
) : ScopeCoroutine<T>(if (context[UndispatchedMarker] == null) context + UndispatchedMarker else context, uCont) {

    /**
     * The state of [ThreadContextElement]s associated with the current undispatched coroutine.
     * It is stored in a thread local because this coroutine can be used concurrently in suspend-resume race scenario.
     */
    private val threadStateToRecover = ThreadLocal<Pair<CoroutineContext, Any?>>()

    /*
     * Indicates that a coroutine has at least one thread context element associated with it
     * and that 'threadStateToRecover' is going to be set in case of dispatchhing in order to preserve them.
     */
    @Volatile
    private var threadLocalIsSet = false

    init {
        if (uCont.context[ContinuationInterceptor] !is CoroutineDispatcher) {
            val values = updateThreadContext(context, null)
            restoreThreadContext(context, values)
            saveThreadContext(context, values)
        }
    }

    fun saveThreadContext(context: CoroutineContext, oldValue: Any?) {
        threadLocalIsSet = true 
        threadStateToRecover.set(context to oldValue)
    }

    fun clearThreadContext(): Boolean {
        return !(threadLocalIsSet && threadStateToRecover.get() == null).also {
            threadStateToRecover.remove()
        }
    }

    override fun afterResume(state: Any?) {
        if (threadLocalIsSet) {
            threadStateToRecover.get()?.let { (ctx, value) ->
                restoreThreadContext(ctx, value)
            }
            // Always clean up threadStateToRecover
            threadStateToRecover.remove()
            threadLocalIsSet = false
        }
        val result = recoverResult(state, uCont)
        withContinuationContext(uCont, null) {
            uCont.resumeWith(result)
        }
    }

    // Clean up threadStateToRecover when the coroutine is completed without suspension
    override fun afterCompletion(state: Any?) {
        if (threadLocalIsSet) {
            threadStateToRecover.remove()
            threadLocalIsSet = false
        }
        super.afterCompletion(state)
    }
}
```
The key changes are:

*   Added a call to `threadStateToRecover.remove()` in `afterResume` to ensure that the thread local state is cleaned up after the coroutine resumes.
*   Added an override for `afterCompletion` to clean up `threadStateToRecover` when the coroutine is completed without suspension.

With these changes, `UndispatchedCoroutine` will properly clean up its thread local state, preventing the leak of `CoroutineContext`.

Here is the list of files and their revised contents:

[start of kotlinx-coroutines-core/jvm/src/CoroutineContext.kt]
```kotlin
package kotlinx.coroutines

import kotlinx.coroutines.internal.*
import kotlin.coroutines.*
import kotlin.coroutines.jvm.internal.CoroutineStackFrame

// ... (rest of the code remains the same)

// Used by withContext when context changes, but dispatcher stays the same
internal actual class UndispatchedCoroutine<in T>actual constructor (
    context: CoroutineContext,
    uCont: Continuation<T>
) : ScopeCoroutine<T>(if (context[UndispatchedMarker] == null) context + UndispatchedMarker else context, uCont) {

    // ... (code remains the same until afterResume)

    override fun afterResume(state: Any?) {
        if (threadLocalIsSet) {
            threadStateToRecover.get()?.let { (ctx, value) ->
                restoreThreadContext(ctx, value)
            }
            threadStateToRecover.remove()
            threadLocalIsSet = false
        }
        val result = recoverResult(state, uCont)
        withContinuationContext(uCont, null) {
            uCont.resumeWith(result)
        }
    }

    override fun afterCompletion(state: Any?) {
        if (threadLocalIsSet) {
            threadStateToRecover.remove()
            threadLocalIsSet = false
        }
        super.afterCompletion(state)
    }
}