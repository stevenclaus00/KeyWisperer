package com.keywhisperer.remote

import android.view.KeyEvent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MediaButtonsTest {
    @Test
    fun tapCounterCountsPressesInsideTheWindow() {
        val c = TapCounter(windowMs = 400)
        assertEquals(1, c.tap(1000))
        assertEquals(2, c.tap(1300))
        assertEquals(3, c.tap(1650)) // each gap is measured from the previous press
        assertEquals(3, c.finish())
    }

    @Test
    fun tapCounterStartsOverAfterAPause() {
        val c = TapCounter(windowMs = 400)
        c.tap(1000)
        assertEquals(1, c.tap(1500)) // 500 ms gap: a new burst
    }

    @Test
    fun finishResetsTheBurst() {
        val c = TapCounter(windowMs = 400)
        c.tap(1000)
        c.tap(1100)
        assertEquals(2, c.finish())
        assertEquals(0, c.finish())
        assertEquals(1, c.tap(1200)) // fresh burst even though only 100 ms passed
    }

    @Test
    fun tapsMapToActions() {
        assertEquals(ButtonAction.TOGGLE_MIC, MediaButtons.actionForTaps(1))
        assertEquals(ButtonAction.SEND, MediaButtons.actionForTaps(2))
        assertEquals(ButtonAction.READ_BACK, MediaButtons.actionForTaps(3))
        assertEquals(ButtonAction.UNDO, MediaButtons.actionForTaps(4))
        assertEquals(ButtonAction.NONE, MediaButtons.actionForTaps(0))
        assertEquals(ButtonAction.NONE, MediaButtons.actionForTaps(9))
    }

    @Test
    fun keysMapToActions() {
        assertEquals(ButtonAction.SEND, MediaButtons.actionForKey(KeyEvent.KEYCODE_MEDIA_NEXT))
        assertEquals(ButtonAction.READ_BACK, MediaButtons.actionForKey(KeyEvent.KEYCODE_MEDIA_PREVIOUS))
        assertNull(MediaButtons.actionForKey(KeyEvent.KEYCODE_VOLUME_UP))
        assertTrue(MediaButtons.isPlayPause(KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE))
        assertTrue(MediaButtons.isPlayPause(KeyEvent.KEYCODE_HEADSETHOOK))
        assertFalse(MediaButtons.isPlayPause(KeyEvent.KEYCODE_MEDIA_NEXT))
    }

    @Test
    fun reconnectBackoffIs1_2_5_10ThenStaysAt10() {
        assertEquals(listOf(1L, 2L, 5L, 10L, 10L, 10L), (0..5).map { backoffSeconds(it) })
    }
}
