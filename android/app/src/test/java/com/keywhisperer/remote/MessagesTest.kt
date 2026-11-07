package com.keywhisperer.remote

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Test

class MessagesTest {
    @Test
    fun buildsHello() {
        val o = Json.parseToJsonElement(Messages.hello("Pixel 8")).jsonObject
        assertEquals("hello", o["type"]!!.jsonPrimitive.content)
        assertEquals("Pixel 8", o["device"]!!.jsonPrimitive.content)
    }

    @Test
    fun buildsControl() {
        val o = Json.parseToJsonElement(Messages.control(Control.READBACK)).jsonObject
        assertEquals("control", o["type"]!!.jsonPrimitive.content)
        assertEquals("readback", o["action"]!!.jsonPrimitive.content)
    }

    @Test
    fun parsesServerMessages() {
        assertEquals(
            ServerMessage.Status(listening = true, connected = true),
            Messages.parse("""{"type":"status","listening":true,"connected":true}"""),
        )
        assertEquals(ServerMessage.Typed("hello world"), Messages.parse("""{"type":"typed","text":"hello world"}"""))
        assertEquals(ServerMessage.Utterance("raw"), Messages.parse("""{"type":"utterance","text":"raw"}"""))
        assertEquals(ServerMessage.Speak("read me"), Messages.parse("""{"type":"speak","text":"read me"}"""))
        assertEquals(ServerMessage.StatusMessage("ok"), Messages.parse("""{"type":"status_message","text":"ok"}"""))
        assertEquals(ServerMessage.Error("boom"), Messages.parse("""{"type":"error","message":"boom"}"""))
    }

    @Test
    fun ignoresUnknownOrBrokenMessages() {
        assertEquals(ServerMessage.Unknown, Messages.parse("""{"type":"something_new","x":1}"""))
        assertEquals(ServerMessage.Unknown, Messages.parse("""{"type":"typed"}""")) // missing text
        assertEquals(ServerMessage.Unknown, Messages.parse("not json"))
        assertEquals(ServerMessage.Unknown, Messages.parse("[1,2]"))
    }
}
