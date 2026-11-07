package com.keywhisperer.remote

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString.Companion.toByteString
import java.util.concurrent.TimeUnit

enum class ConnState { DISCONNECTED, CONNECTING, CONNECTED }

private val BACKOFF_SECONDS = listOf(1L, 2L, 5L, 10L)

/** Seconds to wait before reconnect attempt number [attempt] (0-based): 1, 2, 5, 10, 10, ... */
fun backoffSeconds(attempt: Int): Long = BACKOFF_SECONDS[attempt.coerceIn(0, BACKOFF_SECONDS.lastIndex)]

/**
 * The WebSocket link to the companion. Once [start]ed it keeps reconnecting (with backoff)
 * until [stop] is called, or until the companion rejects our token (close code 4001).
 *
 * Callbacks run on OkHttp / background threads.
 */
class CompanionClient(
    private val deviceName: String,
    private val onState: (ConnState) -> Unit,
    private val onConnected: () -> Unit,
    private val onServerMessage: (ServerMessage) -> Unit,
    private val onBadToken: () -> Unit,
) {
    private val http = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS)     // a WebSocket may be quiet for a long time...
        .pingInterval(15, TimeUnit.SECONDS)   // ...so ping to notice a dead WiFi link
        .build()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private var pairing: Pairing? = null
    private var attempt = 0
    private var reconnectJob: Job? = null

    /** Bumped whenever a socket is replaced or dropped, so late callbacks of old sockets are ignored. */
    private var generation = 0

    @Volatile private var socket: WebSocket? = null
    @Volatile private var connected = false

    /** (Re)connect to [p] and keep the link alive. */
    @Synchronized
    fun start(p: Pairing) {
        dropSocket()
        pairing = p
        attempt = 0
        connect()
    }

    /** Disconnect and stop reconnecting. */
    @Synchronized
    fun stop() {
        pairing = null
        dropSocket()
        onState(ConnState.DISCONNECTED)
    }

    /** True once [start] has been called (and [stop] has not). */
    @get:Synchronized
    val isStarted: Boolean get() = pairing != null

    /** Send one audio frame. Frames are dropped, not buffered, when we are offline or backed up. */
    fun sendAudio(buf: ByteArray, length: Int): Boolean {
        val s = socket ?: return false
        if (!connected || s.queueSize() > MAX_QUEUED_BYTES) return false
        return s.send(buf.toByteString(0, length))
    }

    fun sendControl(action: String): Boolean {
        val s = socket ?: return false
        return connected && s.send(Messages.control(action))
    }

    // ---- internals -------------------------------------------------------------------------

    private fun dropSocket() {
        generation++
        reconnectJob?.cancel()
        socket?.close(1000, "bye")
        socket = null
        connected = false
    }

    @Synchronized
    private fun connect() {
        val p = pairing ?: return
        val gen = ++generation
        onState(ConnState.CONNECTING)
        val request = Request.Builder().url(p.wsUrl()).build()
        socket = http.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                synchronized(this@CompanionClient) {
                    if (gen != generation) return
                    attempt = 0
                    connected = true
                }
                onState(ConnState.CONNECTED)
                webSocket.send(Messages.hello(deviceName))
                onConnected()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                if (gen == generation) onServerMessage(Messages.parse(text))
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
                dropped(gen, code)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = dropped(gen, code)

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) = dropped(gen, null)
        })
    }

    /** The socket of generation [gen] went away: reconnect later, unless the token was refused. */
    @Synchronized
    private fun dropped(gen: Int, closeCode: Int?) {
        if (gen != generation) return // an old socket, already replaced
        generation++
        connected = false
        socket = null
        onState(ConnState.DISCONNECTED)
        if (closeCode == CLOSE_BAD_TOKEN) {
            onBadToken() // retrying with the same token is pointless
            return
        }
        if (pairing == null) return
        val wait = backoffSeconds(attempt++)
        reconnectJob = scope.launch {
            delay(wait * 1000)
            connect()
        }
    }

    private companion object {
        const val CLOSE_BAD_TOKEN = 4001
        const val MAX_QUEUED_BYTES = 64 * 1024L // ~2 s of audio; beyond that we are clearly not keeping up
    }
}
