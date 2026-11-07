package com.keywhisperer.remote

import android.content.Context
import android.os.Build
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.channels.BufferOverflow

/** Everything the screen shows. */
data class UiState(
    val pairing: Pairing? = null,
    val conn: ConnState = ConnState.DISCONNECTED,
    val micOn: Boolean = false,
    val companionListening: Boolean? = null, // null = not heard yet
    val typed: List<String> = emptyList(),   // newest first
    val speaking: Boolean = false,
)

/**
 * The one place that owns the connection, the speaker and the UI state.
 * It lives as long as the app process, so the activity and [MicService] both just talk to it.
 * (Think of it as a module-level singleton in Python.)
 */
object Session {
    private const val MAX_TYPED_LINES = 5

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private val _messages = MutableSharedFlow<String>(extraBufferCapacity = 8, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    /** Short messages for a snackbar. */
    val messages: SharedFlow<String> = _messages.asSharedFlow()

    private lateinit var store: PairingStore
    private lateinit var speaker: Speaker
    private lateinit var client: CompanionClient

    /** Called once from [KwApp]. */
    fun init(context: Context) {
        store = PairingStore(context)
        speaker = Speaker(context) { speaking -> _state.update { it.copy(speaking = speaking) } }
        client = CompanionClient(
            deviceName = Build.MODEL,
            onState = { conn -> _state.update { it.copy(conn = conn) } },
            onConnected = { syncMicState() },
            onServerMessage = ::handle,
            onBadToken = { showMessage("Companion refused the token. Pair again.") },
        )
        _state.update { it.copy(pairing = store.load()) }
    }

    // ---- pairing / connection --------------------------------------------------------------

    /** Auto-connect with the saved pairing (safe to call repeatedly). */
    fun connectIfPaired() {
        val p = _state.value.pairing ?: return
        if (!client.isStarted) client.start(p)
    }

    fun pair(p: Pairing) {
        store.save(p)
        _state.update { it.copy(pairing = p, companionListening = null) }
        client.start(p)
    }

    fun unpair() {
        client.stop()
        store.clear()
        _state.update { it.copy(pairing = null, companionListening = null) }
    }

    // ---- commands (from buttons and earbuds) ------------------------------------------------

    fun send() = control(Control.SEND)
    fun undo() = control(Control.UNDO)
    fun readBack() = control(Control.READBACK)
    fun stopSpeaking() = speaker.stop()

    private fun control(action: String) {
        if (!client.sendControl(action)) showMessage("Not connected")
    }

    // ---- used by MicService ----------------------------------------------------------------

    /** The service reports whether the mic is really recording. */
    fun setMic(on: Boolean) {
        _state.update { it.copy(micOn = on) }
        client.sendControl(if (on) Control.RESUME else Control.PAUSE)
    }

    fun sendAudio(buf: ByteArray, length: Int) = client.sendAudio(buf, length)

    fun showMessage(text: String) {
        _messages.tryEmit(text)
    }

    // ---- internals -------------------------------------------------------------------------

    /** After (re)connecting, tell the companion whether we are listening. */
    private fun syncMicState() {
        client.sendControl(if (_state.value.micOn) Control.RESUME else Control.PAUSE)
    }

    private fun handle(msg: ServerMessage) {
        when (msg) {
            is ServerMessage.Status -> _state.update { it.copy(companionListening = msg.listening) }
            is ServerMessage.Typed -> _state.update {
                it.copy(typed = (listOf(msg.text) + it.typed).take(MAX_TYPED_LINES))
            }
            is ServerMessage.Speak -> speaker.speak(msg.text)
            is ServerMessage.StatusMessage -> showMessage(msg.text)
            is ServerMessage.Error -> showMessage("Error: ${msg.message}")
            is ServerMessage.Utterance, ServerMessage.Unknown -> Unit // raw transcript: not shown
        }
    }
}
