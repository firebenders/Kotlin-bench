```kotlin
// ... (rest of the file remains the same until the CoroutineContext extensions section)

/**
 * Returns `true` when the coroutine is [active][Job.isActive].
 * It checks whether there is a [Job] in the context and whether it is active.
 * If there is no [Job], it returns `true`, indicating the coroutine is not bound by a job's lifecycle.
 *
 * This property is useful for checking whether a coroutine can continue its execution.
 */
public val CoroutineContext.isActiveOrEmpty: Boolean
    get() = get(Job)?.isActive ?: true

/**
 * Returns `true` when the [Job] of the coroutine in this context is still active
 * (has not completed and was not cancelled yet).
 *
 * Check this property in long-running computation loops to support cancellation
 * when [CoroutineScope.isActive] is not available:
 *
 * ```
 * while (coroutineContext.isActive) {
 *     // do some computation
 * }
 * ```
 *
 * The `coroutineContext.isActive` expression is a shortcut for `coroutineContext[Job]?.isActive == true`.
 * See [Job.isActive].
 *
 * @deprecated Use `coroutineContext.isActiveOrEmpty` instead for a more robust check that handles contexts without a Job.
 */
@Deprecated("Use isActiveOrEmpty instead", ReplaceWith("isActiveOrEmpty"))
public val CoroutineContext.isActive: Boolean
    get() = this[Job]?.isActive == true

// ... (rest of the file remains the same)
```