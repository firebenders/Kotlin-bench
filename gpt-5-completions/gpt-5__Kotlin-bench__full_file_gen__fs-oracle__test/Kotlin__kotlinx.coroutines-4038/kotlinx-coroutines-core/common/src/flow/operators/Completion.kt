@file:JvmMultifileClass
@file:JvmName("FlowKt")

package kotlinx.coroutines.flow

import kotlinx.coroutines.flow.internal.AbortFlowException
import kotlinx.coroutines.flow.internal.checkOwnership
import kotlinx.coroutines.flow.flow as safeFlow
import kotlinx.coroutines.flow.internal.unsafeFlow as flow

/**
 * Runs the given [action] when the flow completes or is cancelled.
 *
 * Important nuance: the action is executed in a cancellable context, so if a downstream terminal
 * operator cancels the collection (e.g. first(), take(1), etc), the action will be cancelled as well.
 * This prevents situations where a long-running/suspending action could hang the terminal operator.
 */
public fun <T> Flow<T>.onCompletion(action: suspend (cause: Throwable?) -> Unit): Flow<T> =
    onCompletion { cause -> action(cause) }

/**
 * Runs the given [action] when the flow completes or is cancelled.
 *
 * The [action] receiver is a [FlowCollector], allowing it to emit additional elements after
 * the upstream has completed.
 *
 * The action is executed in a cancellable context to ensure that downstream cancellation
 * (e.g. from a terminal operator like first()) can interrupt it. This fixes a scenario where
 * upstream completes "normally" (e.g. due to take(1)), but a downstream terminal operator cancels
 * after receiving the first element; the action should not be able to indefinitely block completion.
 */
public fun <T> Flow<T>.onCompletion(
    action: suspend FlowCollector<T>.(cause: Throwable?) -> Unit
): Flow<T> = safeFlow {
    var cause: Throwable? = null
    try {
        this@onCompletion.collect { value ->
            emit(value)
        }
    } catch (e: Throwable) {
        // Propagate, but remember the cause to pass into action
        cause = e
        throw e
    } finally {
        // Execute action in a cancellable context so downstream cancellation can stop it.
        // Do not wrap in NonCancellable here to avoid hangs with terminal operators.
        try {
            action(cause)
        } catch (e: AbortFlowException) {
            // Swallow only if it's ours; otherwise rethrow
            e.checkOwnership(this)
            throw e
        }
    }
}