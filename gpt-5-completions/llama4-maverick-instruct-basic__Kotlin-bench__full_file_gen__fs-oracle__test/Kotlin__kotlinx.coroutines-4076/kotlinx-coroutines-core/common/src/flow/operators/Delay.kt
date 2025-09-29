@file:JvmMultifileClass
@file:JvmName("FlowKt")

package kotlinx.coroutines.flow

import kotlinx.coroutines.*
import kotlinx.coroutines.channels.*
import kotlinx.coroutines.flow.internal.*
import kotlinx.coroutines.selects.*
import kotlin.jvm.*
import kotlin.time.*

private fun <T> Flow<T>.timeoutInternal(
    timeout: Duration
): Flow<T> = scopedFlow { downStream ->
    if (timeout <= Duration.ZERO) throw TimeoutCancellationException("Timed out immediately")
    val values = buffer(Channel.RENDEZVOUS).produceIn(this)
    whileSelect {
        values.onReceiveCatching { value ->
            value.onSuccess {
                downStream.emit(it)
            }.onFailure { cause ->
                cause?.let { downStream.emit(FlowFailure(cause)) }
            }
            return@onReceiveCatching value.isSuccess
        }
        onTimeout(timeout) {
            throw TimeoutCancellationException("Timed out waiting for $timeout")
        }
    }
}.catch { e ->
    e.unwrap().let { throw it }
}