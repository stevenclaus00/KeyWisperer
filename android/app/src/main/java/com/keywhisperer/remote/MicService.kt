package com.keywhisperer.remote

import android.Manifest
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.view.KeyEvent
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import androidx.core.content.IntentCompat

/**
 * Foreground service that
 *  1. records the microphone (16 kHz mono PCM16) and streams 20 ms frames to the companion,
 *  2. owns a MediaSession so Bluetooth earbud taps arrive here (see [MediaButtons]).
 *
 * Lifecycle: the first "mic on" starts the service in the foreground (needs the app visible,
 * Android 12+ rule). After that it stays alive with the mic idle, so an earbud tap can switch
 * the mic back on while the screen is off. The notification's Stop action ends it.
 */
class MicService : Service() {

    private val handler = Handler(Looper.getMainLooper())
    private val taps = TapCounter()
    private var mediaSession: MediaSession? = null
    private var recordThread: Thread? = null
    @Volatile private var recording = false
    private var inForeground = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        val channel = NotificationChannel(CHANNEL_ID, "Microphone", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        createMediaSession()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_MIC_ON -> startMic()
            ACTION_MIC_OFF -> if (inForeground) stopMic() else stopSelf()
            ACTION_STOP -> {
                stopMic()
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        inForeground = false // the system is tearing us down: do not re-post the notification
        stopMic()
        mediaSession?.release()
        mediaSession = null
        super.onDestroy()
    }

    // ---- microphone ------------------------------------------------------------------------

    private fun startMic() {
        showForeground() // must happen promptly after startForegroundService()
        if (recording) return

        val record = createAudioRecord()
        if (record == null) {
            Session.showMessage("Could not open the microphone")
            refreshUi()
            return
        }
        recording = true
        Session.setMic(true) // UI on + "control resume"
        refreshUi()

        recordThread = Thread({
            val frame = ByteArray(FRAME_BYTES)
            try {
                record.startRecording()
                while (recording) {
                    val n = record.read(frame, 0, frame.size) // blocks ~20 ms
                    if (n < 0) break // error
                    if (n > 0) Session.sendAudio(frame, n) // dropped if offline
                }
            } finally {
                record.release()
            }
        }, "mic-record").also { it.start() }
    }

    private fun stopMic() {
        if (!recording) return
        recording = false
        recordThread?.join(1000)
        recordThread = null
        Session.setMic(false) // UI off + "control pause"
        refreshUi()
    }

    /** Prefer VOICE_RECOGNITION (less processing), fall back to MIC. */
    @SuppressLint("MissingPermission") // the UI asks for RECORD_AUDIO before starting us
    private fun createAudioRecord(): AudioRecord? {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            return null
        }
        val minBuf = AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val bufSize = maxOf(minBuf, FRAME_BYTES * 8)
        for (source in listOf(MediaRecorder.AudioSource.VOICE_RECOGNITION, MediaRecorder.AudioSource.MIC)) {
            val r = AudioRecord(source, SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, bufSize)
            if (r.state == AudioRecord.STATE_INITIALIZED) return r
            r.release()
        }
        return null
    }

    // ---- notification ----------------------------------------------------------------------

    private fun buildNotification(): Notification {
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val stop = PendingIntent.getService(
            this, 1, Intent(this, MicService::class.java).setAction(ACTION_STOP), PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_mic)
            .setContentTitle("KeyWhisperer")
            .setContentText(if (recording) "Mic on: streaming to your computer" else "Mic off")
            .setContentIntent(open)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .addAction(0, "Stop", stop)
            .build()
    }

    private fun showForeground() {
        ServiceCompat.startForeground(
            this, NOTIFICATION_ID, buildNotification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE,
        )
        inForeground = true
    }

    /** Update notification text and the MediaSession playback state after the mic changed. */
    private fun refreshUi() {
        if (inForeground) showForeground()
        updatePlaybackState()
    }

    // ---- media session (earbud taps) -------------------------------------------------------

    private fun createMediaSession() {
        val session = MediaSession(this, "KeyWhispererRemote")
        session.setCallback(object : MediaSession.Callback() {
            override fun onMediaButtonEvent(mediaButtonIntent: Intent): Boolean {
                val event = IntentCompat.getParcelableExtra(mediaButtonIntent, Intent.EXTRA_KEY_EVENT, KeyEvent::class.java)
                    ?: return false
                val known = MediaButtons.isPlayPause(event.keyCode) || MediaButtons.actionForKey(event.keyCode) != null
                if (!known) return false
                if (event.action == KeyEvent.ACTION_DOWN && event.repeatCount == 0) onKey(event.keyCode)
                return true
            }
        })
        session.isActive = true
        mediaSession = session
        updatePlaybackState()
    }

    /**
     * Android sends media buttons only to a session that is PLAYING, so we report PLAYING while
     * the mic is on (and, by default, while the service is alive, see MediaButtons).
     * No audio is actually played; this is only a routing hint for the system.
     */
    private fun updatePlaybackState() {
        val playing = recording || MediaButtons.STAY_PLAYING_WHEN_MIC_OFF
        val actions = PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE or
            PlaybackState.ACTION_SKIP_TO_NEXT or PlaybackState.ACTION_SKIP_TO_PREVIOUS
        val state = PlaybackState.Builder()
            .setActions(actions)
            .setState(
                if (playing) PlaybackState.STATE_PLAYING else PlaybackState.STATE_PAUSED,
                PlaybackState.PLAYBACK_POSITION_UNKNOWN,
                1f,
            )
            .build()
        mediaSession?.setPlaybackState(state)
    }

    /** One media key went down. Play/pause presses are counted, other keys act immediately. */
    private fun onKey(keyCode: Int) {
        if (!MediaButtons.isPlayPause(keyCode)) {
            MediaButtons.actionForKey(keyCode)?.let { perform(it) }
            return
        }
        val count = taps.tap(SystemClock.uptimeMillis())
        handler.removeCallbacks(resolveTaps)
        if (count >= MediaButtons.MAX_TAPS) {
            resolveTaps.run() // no point waiting for more
        } else {
            handler.postDelayed(resolveTaps, MediaButtons.TAP_WINDOW_MS)
        }
    }

    private val resolveTaps = Runnable { perform(MediaButtons.actionForTaps(taps.finish())) }

    private fun perform(action: ButtonAction) {
        when (action) {
            ButtonAction.TOGGLE_MIC -> if (recording) stopMic() else startMic()
            ButtonAction.SEND -> Session.send()
            ButtonAction.UNDO -> Session.undo()
            ButtonAction.READ_BACK -> Session.readBack()
            ButtonAction.NONE -> Unit
        }
    }

    companion object {
        private const val ACTION_MIC_ON = "com.keywhisperer.remote.MIC_ON"
        private const val ACTION_MIC_OFF = "com.keywhisperer.remote.MIC_OFF"
        private const val ACTION_STOP = "com.keywhisperer.remote.STOP"
        private const val CHANNEL_ID = "mic"
        private const val NOTIFICATION_ID = 1

        private const val SAMPLE_RATE = 16000
        private const val FRAME_BYTES = SAMPLE_RATE / 50 * 2 // 20 ms of 16-bit mono = 640 bytes

        /** Start recording (call only while the app is visible and RECORD_AUDIO is granted). */
        fun micOn(context: Context) {
            ContextCompat.startForegroundService(context, intent(context, ACTION_MIC_ON))
        }

        fun micOff(context: Context) {
            context.startService(intent(context, ACTION_MIC_OFF))
        }

        private fun intent(context: Context, action: String) =
            Intent(context, MicService::class.java).setAction(action)
    }
}
