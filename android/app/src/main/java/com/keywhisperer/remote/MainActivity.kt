package com.keywhisperer.remote

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

/** The single screen. All real work is in [Session] and [MicService]; this wires up Android bits. */
class MainActivity : ComponentActivity() {

    // Asks for the mic (and notification) permission, then starts streaming if the mic was granted.
    private val permissionRequest =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { granted ->
            if (granted[Manifest.permission.RECORD_AUDIO] == true) {
                MicService.micOn(this)
            } else {
                Session.showMessage("Microphone permission is needed")
            }
        }

    // QR scanner (zxing-android-embedded, no Google Play Services).
    private val qrScanner = registerForActivityResult(ScanContract()) { result ->
        result.contents?.let { pairFromText(it) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Keep the screen awake exactly while the mic is on.
        lifecycleScope.launch {
            Session.state.map { it.micOn }.distinctUntilChanged().collect { micOn ->
                if (micOn) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            }
        }

        setContent {
            KeyWhispererTheme {
                MainScreen(
                    onToggleMic = ::toggleMic,
                    onScanQr = ::scanQr,
                    onPairText = ::pairFromText,
                )
            }
        }
    }

    override fun onStart() {
        super.onStart()
        Session.connectIfPaired() // auto-connect with the saved pairing
    }

    private fun toggleMic() {
        if (Session.state.value.micOn) {
            MicService.micOff(this)
            return
        }
        val missing = buildList {
            add(Manifest.permission.RECORD_AUDIO)
            if (Build.VERSION.SDK_INT >= 33) add(Manifest.permission.POST_NOTIFICATIONS)
        }.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }

        if (missing.isEmpty()) MicService.micOn(this) else permissionRequest.launch(missing.toTypedArray())
    }

    private fun scanQr() {
        qrScanner.launch(
            ScanOptions()
                .setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                .setPrompt("Scan the QR code shown by the companion")
                .setBeepEnabled(false)
                .setOrientationLocked(false)
        )
    }

    private fun pairFromText(text: String) {
        val pairing = Pairing.parse(text)
        if (pairing == null) {
            Session.showMessage("That is not a KeyWhisperer pairing code (kw://host:port?token=...)")
        } else {
            Session.pair(pairing)
            Session.showMessage("Pairing saved for ${pairing.label()}")
        }
    }
}
