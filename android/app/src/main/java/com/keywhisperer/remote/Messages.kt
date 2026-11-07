package com.keywhisperer.remote

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.put

/** The `action` values of a `control` message. */
object Control {
    const val SEND = "send"
    const val UNDO = "undo"
    const val PAUSE = "pause"
    const val RESUME = "resume"
    const val READBACK = "readback"
}

/** Messages the companion sends to the phone. Unknown types become [Unknown] and are ignored. */
sealed interface ServerMessage {
    data class Status(val listening: Boolean, val connected: Boolean) : ServerMessage
    data class Utterance(val text: String) : ServerMessage
    data class Typed(val text: String) : ServerMessage
    data class Speak(val text: String) : ServerMessage
    data class StatusMessage(val text: String) : ServerMessage
    data class Error(val message: String) : ServerMessage
    data object Unknown : ServerMessage
}

/** Building and parsing the JSON text frames. Pure Kotlin, unit tested. */
object Messages {

    fun hello(device: String): String = buildJsonObject {
        put("type", "hello")
        put("device", device)
    }.toString()

    fun control(action: String): String = buildJsonObject {
        put("type", "control")
        put("action", action)
    }.toString()

    fun parse(text: String): ServerMessage {
        val obj = try {
            Json.parseToJsonElement(text).jsonObject
        } catch (e: Exception) {
            return ServerMessage.Unknown // not JSON, or not an object
        }
        return when (obj.string("type")) {
            "status" -> ServerMessage.Status(
                listening = obj.bool("listening") ?: false,
                connected = obj.bool("connected") ?: true,
            )
            "utterance" -> obj.string("text")?.let { ServerMessage.Utterance(it) }
            "typed" -> obj.string("text")?.let { ServerMessage.Typed(it) }
            "speak" -> obj.string("text")?.let { ServerMessage.Speak(it) }
            "status_message" -> obj.string("text")?.let { ServerMessage.StatusMessage(it) }
            "error" -> obj.string("message")?.let { ServerMessage.Error(it) }
            else -> null
        } ?: ServerMessage.Unknown
    }

    private fun JsonObject.string(key: String): String? = (this[key] as? JsonPrimitive)?.contentOrNull
    private fun JsonObject.bool(key: String): Boolean? = (this[key] as? JsonPrimitive)?.booleanOrNull
}
