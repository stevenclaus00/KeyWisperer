package com.keywhisperer.remote

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.flow.collectLatest

// A calm dark "tool" palette.
private val Ink = Color(0xFF14181C)
private val Panel = Color(0xFF1D2329)
private val Teal = Color(0xFF4DB6AC)
private val Amber = Color(0xFFFFB74D)
private val Soft = Color(0xFF8A96A0)

private val DarkColors = darkColorScheme(
    primary = Teal,
    onPrimary = Ink,
    background = Ink,
    onBackground = Color(0xFFE6EAED),
    surface = Panel,
    onSurface = Color(0xFFE6EAED),
    surfaceVariant = Panel,
    secondaryContainer = Color(0xFF28323A),
    onSecondaryContainer = Color(0xFFE6EAED),
)

@Composable
fun KeyWhispererTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = DarkColors, content = content)
}

@Composable
fun MainScreen(
    onToggleMic: () -> Unit,
    onScanQr: () -> Unit,
    onPairText: (String) -> Unit,
) {
    val ui by Session.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    // Show the newest message; a newer one replaces the current one.
    LaunchedEffect(Unit) {
        Session.messages.collectLatest { snackbar.showSnackbar(it, duration = SnackbarDuration.Short) }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            StatusRow(ui)
            MicButton(on = ui.micOn, onClick = onToggleMic)
            TypedLines(ui.typed)
            ActionButtons(connected = ui.conn == ConnState.CONNECTED)
            if (ui.speaking) {
                OutlinedButton(onClick = Session::stopSpeaking) { Text("Stop speaking") }
            }
            PairingCard(ui.pairing, onScanQr, onPairText)
        }
    }
}

@Composable
private fun StatusRow(ui: UiState) {
    val (text, color) = when {
        ui.pairing == null -> "Not paired" to Soft
        ui.conn == ConnState.CONNECTED -> {
            val heard = when (ui.companionListening) {
                true -> "listening"
                false -> "paused"
                null -> "connected"
            }
            "${ui.pairing.label()} · $heard" to Teal
        }
        ui.conn == ConnState.CONNECTING -> "Connecting to ${ui.pairing.label()}..." to Amber
        else -> "Offline, retrying ${ui.pairing.label()}" to Amber
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(Modifier.size(10.dp).background(color, CircleShape))
        Text(text, color = color, fontSize = 15.sp)
    }
}

@Composable
private fun MicButton(on: Boolean, onClick: () -> Unit) {
    val accent = if (on) Teal else Soft
    Box(
        modifier = Modifier
            .size(176.dp)
            .background(if (on) Teal.copy(alpha = 0.18f) else Panel, CircleShape)
            .border(3.dp, accent, CircleShape)
            .clickable(role = Role.Button, onClickLabel = if (on) "Turn microphone off" else "Turn microphone on", onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(if (on) "MIC ON" else "MIC OFF", color = accent, fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Text(if (on) "tap to stop" else "tap to talk", color = Soft, fontSize = 13.sp)
        }
    }
}

@Composable
private fun TypedLines(lines: List<String>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Panel),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Typed on your computer", color = Soft, fontSize = 12.sp)
            if (lines.isEmpty()) {
                Text("Nothing yet. Start talking.", color = Soft)
            }
            lines.forEachIndexed { i, line ->
                // Newest first; older lines fade a little.
                Text(line, color = MaterialTheme.colorScheme.onSurface.copy(alpha = if (i == 0) 1f else 0.6f))
            }
        }
    }
}

@Composable
private fun ActionButtons(connected: Boolean) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        FilledTonalButton(onClick = Session::send, enabled = connected, modifier = Modifier.weight(1f)) { Text("Send") }
        FilledTonalButton(onClick = Session::undo, enabled = connected, modifier = Modifier.weight(1f)) { Text("Undo") }
        FilledTonalButton(onClick = Session::readBack, enabled = connected, modifier = Modifier.weight(1f)) { Text("Read back") }
    }
}

@Composable
private fun PairingCard(pairing: Pairing?, onScanQr: () -> Unit, onPairText: (String) -> Unit) {
    var text by rememberSaveable { mutableStateOf("") }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Panel),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Pairing", color = Soft, fontSize = 12.sp)
            Button(onClick = onScanQr, modifier = Modifier.fillMaxWidth()) { Text("Pair (scan QR)") }
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                label = { Text("or paste kw://host:port?token=...") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(onClick = { onPairText(text); text = "" }, enabled = text.isNotBlank()) { Text("Use code") }
                if (pairing != null) {
                    TextButton(onClick = Session::unpair) { Text("Forget ${pairing.label()}") }
                }
            }
        }
    }
    Spacer(Modifier.height(8.dp))
}
