package com.keywhisperer.remote

import android.content.Context
import android.media.AudioAttributes
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener

/**
 * Reads text aloud with Android TextToSpeech on the media stream, so it plays through
 * the Bluetooth earbuds. It never touches the microphone: recording simply carries on.
 */
class Speaker(context: Context, private val onSpeaking: (Boolean) -> Unit) {
    private lateinit var tts: TextToSpeech
    @Volatile private var ready = false
    @Volatile private var pending: String? = null // text that arrived before the engine was ready
    private var counter = 0

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts.setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                )
                tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) = onSpeaking(true)
                    override fun onDone(utteranceId: String?) = onSpeaking(false)
                    override fun onStop(utteranceId: String?, interrupted: Boolean) = onSpeaking(false)

                    @Deprecated("Required override on older API levels")
                    override fun onError(utteranceId: String?) = onSpeaking(false)
                })
                ready = true
                pending?.let { speak(it) }
                pending = null
            }
        }
    }

    /** Speak [text], replacing anything currently being read. */
    fun speak(text: String) {
        if (!ready) {
            pending = text
            return
        }
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "kw-${counter++}")
    }

    fun stop() {
        pending = null
        if (ready) tts.stop()
        onSpeaking(false)
    }
}
