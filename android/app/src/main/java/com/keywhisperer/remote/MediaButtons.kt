package com.keywhisperer.remote

import android.view.KeyEvent

/** What an earbud gesture can ask the app to do. */
enum class ButtonAction { TOGGLE_MIC, SEND, UNDO, READ_BACK, NONE }

/**
 * THE earbud mapping. Change the gestures here and nowhere else.
 *
 *  - Dedicated keys: NEXT -> send, PREVIOUS -> read back.
 *  - Many earbuds only ever send PLAY/PAUSE (or HEADSETHOOK), so we count presses
 *    that arrive within [TAP_WINDOW_MS] of each other:
 *      1 tap -> toggle mic, 2 taps -> send, 3 taps -> read back, 4 taps -> undo.
 *    A single tap therefore acts after [TAP_WINDOW_MS] (we must wait to see if more follow).
 */
object MediaButtons {
    const val TAP_WINDOW_MS = 400L
    const val MAX_TAPS = 4

    fun isPlayPause(keyCode: Int): Boolean =
        keyCode == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE ||
            keyCode == KeyEvent.KEYCODE_HEADSETHOOK ||
            keyCode == KeyEvent.KEYCODE_MEDIA_PLAY ||
            keyCode == KeyEvent.KEYCODE_MEDIA_PAUSE

    /** Keys that map straight to an action (not tap-counted). Null = not ours. */
    fun actionForKey(keyCode: Int): ButtonAction? = when (keyCode) {
        KeyEvent.KEYCODE_MEDIA_NEXT -> ButtonAction.SEND
        KeyEvent.KEYCODE_MEDIA_PREVIOUS -> ButtonAction.READ_BACK
        else -> null
    }

    /** The action for a finished burst of play/pause presses. */
    fun actionForTaps(taps: Int): ButtonAction = when (taps) {
        1 -> ButtonAction.TOGGLE_MIC
        2 -> ButtonAction.SEND
        3 -> ButtonAction.READ_BACK
        4 -> ButtonAction.UNDO
        else -> ButtonAction.NONE
    }

    /**
     * Android only routes media buttons to a MediaSession that is "playing".
     * We set PLAYING while the mic is on. If this is true we ALSO stay PLAYING while the
     * service is alive but the mic is off, so an earbud tap can switch the mic back on.
     * Set to false for the strict behaviour (PAUSED when mic is off).
     */
    const val STAY_PLAYING_WHEN_MIC_OFF = true
}

/**
 * Counts presses that follow each other within [windowMs]. Pure logic (time is passed in),
 * so it is unit tested. The caller waits [windowMs] after the last press, then calls [finish].
 */
class TapCounter(private val windowMs: Long = MediaButtons.TAP_WINDOW_MS) {
    private var count = 0
    private var lastMs = 0L

    /** Register a press at [nowMs]; returns how many presses are in the current burst. */
    fun tap(nowMs: Long): Int {
        count = if (count > 0 && nowMs - lastMs <= windowMs) count + 1 else 1
        lastMs = nowMs
        return count
    }

    /** End the burst: returns its size and starts fresh. */
    fun finish(): Int {
        val n = count
        count = 0
        return n
    }
}
