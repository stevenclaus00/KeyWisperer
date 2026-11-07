package com.keywhisperer.remote

import android.content.Context
import java.net.URLDecoder
import java.net.URLEncoder

/**
 * Where the companion lives: parsed from the QR code / pasted text
 * `kw://<lan-ip>:<port>?token=<token>`.
 */
data class Pairing(val host: String, val port: Int, val token: String) {

    /** The WebSocket address the companion listens on. */
    fun wsUrl(): String = "ws://$host:$port/audio?token=${URLEncoder.encode(token, "UTF-8")}"

    /** Short text for the UI (never shows the token). */
    fun label(): String = "$host:$port"

    companion object {
        const val DEFAULT_PORT = 8765

        /** Returns null when [text] is not a valid pairing URI. Pure Kotlin, unit tested. */
        fun parse(text: String): Pairing? {
            val s = text.trim()
            if (!s.startsWith("kw://", ignoreCase = true)) return null
            val rest = s.substring("kw://".length)

            // Split "host:port/?a=b" into the authority part and the query part.
            val q = rest.indexOf('?')
            val authority = (if (q >= 0) rest.substring(0, q) else rest).trimEnd('/')
            val query = if (q >= 0) rest.substring(q + 1) else ""

            val token = query.split('&')
                .map { it.split('=', limit = 2) }
                .firstOrNull { it.size == 2 && it[0] == "token" }
                ?.get(1)
                ?.let { URLDecoder.decode(it, "UTF-8") }
            if (token.isNullOrEmpty()) return null

            val colon = authority.lastIndexOf(':')
            val host = if (colon >= 0) authority.substring(0, colon) else authority
            val port = if (colon >= 0) authority.substring(colon + 1).toIntOrNull() else DEFAULT_PORT
            if (host.isEmpty() || port == null || port !in 1..65535) return null
            return Pairing(host, port, token)
        }
    }
}

/** Remembers the pairing in SharedPreferences so the app can auto-connect on launch. */
class PairingStore(context: Context) {
    private val prefs = context.getSharedPreferences("pairing", Context.MODE_PRIVATE)

    fun load(): Pairing? {
        val host = prefs.getString("host", null) ?: return null
        val token = prefs.getString("token", null) ?: return null
        return Pairing(host, prefs.getInt("port", Pairing.DEFAULT_PORT), token)
    }

    fun save(p: Pairing) {
        prefs.edit().putString("host", p.host).putInt("port", p.port).putString("token", p.token).apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }
}
