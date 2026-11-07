package com.keywhisperer.remote

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PairingTest {
    @Test
    fun parsesNormalUri() {
        val p = Pairing.parse("kw://192.168.1.20:8765?token=abc123")
        assertEquals(Pairing("192.168.1.20", 8765, "abc123"), p)
    }

    @Test
    fun trimsWhitespaceAndDecodesToken() {
        val p = Pairing.parse("  kw://10.0.0.5:9000/?token=a%2Bb-c_d \n")
        assertEquals(Pairing("10.0.0.5", 9000, "a+b-c_d"), p)
    }

    @Test
    fun usesDefaultPortWhenMissing() {
        assertEquals(8765, Pairing.parse("kw://host.local?token=t")?.port)
    }

    @Test
    fun rejectsBadInput() {
        assertNull(Pairing.parse("http://192.168.1.20:8765?token=abc"))
        assertNull(Pairing.parse("kw://192.168.1.20:8765"))          // no token
        assertNull(Pairing.parse("kw://192.168.1.20:8765?token="))   // empty token
        assertNull(Pairing.parse("kw://:8765?token=abc"))            // no host
        assertNull(Pairing.parse("kw://host:notaport?token=abc"))
        assertNull(Pairing.parse("kw://host:70000?token=abc"))
        assertNull(Pairing.parse(""))
    }

    @Test
    fun buildsWebSocketUrl() {
        assertEquals("ws://1.2.3.4:8765/audio?token=a+b", Pairing("1.2.3.4", 8765, "a b").wsUrl())
        assertEquals("1.2.3.4:8765", Pairing("1.2.3.4", 8765, "secret").label())
    }
}
