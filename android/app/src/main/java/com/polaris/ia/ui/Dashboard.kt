// Polaris IA — Dashboard Panel
// Panel lateral derecho con métricas de aprendizaje en tiempo real

package com.polaris.ia.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.*
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.polaris.ia.data.LearningMetrics
import com.polaris.ia.data.LearningProgress

// ─────────────────────────────────────────────
//  COLORES DEL DASHBOARD
// ─────────────────────────────────────────────

private val DashBg      = Color(0xFF070D1A)
private val DashBorder  = Color(0xFF1A3A6A)
private val DashAccent  = Color(0xFF00DDFF)
private val DashGreen   = Color(0xFF00FF88)
private val DashGold    = Color(0xFFFFCC00)
private val DashText    = Color(0xFFB0C4DE)
private val DashDim     = Color(0xFF4A6080)

// ─────────────────────────────────────────────
//  COMPONENTE PRINCIPAL
// ─────────────────────────────────────────────

@Composable
fun DashboardPanel(
    metrics: LearningMetrics,
    progress: LearningProgress,
    isConnected: Boolean,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxHeight()
            .width(200.dp)
            .background(DashBg)
            .border(width = 1.dp, color = DashBorder, shape = RoundedCornerShape(0.dp))
            .padding(horizontal = 12.dp, vertical = 16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Header
        DashHeader(isConnected)

        DashDivider()

        // ── BARRA DE PROGRESO REAL (solo si está activo) ──
        if (progress.active) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "⚡ ${progress.phase.uppercase()}",
                        color = DashAccent,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                    Text(
                        text = "${progress.percent}%",
                        color = DashGreen,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                }
                
                // Barra de progreso
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp))
                        .background(DashBorder)
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxHeight()
                            .fillMaxWidth(progress.percent / 100f)
                            .background(
                                Brush.horizontalGradient(listOf(DashGreen, DashAccent))
                            )
                    )
                }

                Text(
                    text = progress.topic,
                    color = DashText,
                    fontSize = 8.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    fontFamily = FontFamily.Monospace
                )
            }
            DashDivider()
        }

        // Neuronas
        DashMetric(
            icon = "🧠",
            label = "NEURONAS",
            value = metrics.neurons.toString(),
            color = DashAccent,
            progress = (metrics.neurons.toFloat() / 10_000f).coerceIn(0f, 1f)
        )

        // Parámetros / conexiones
        DashMetric(
            icon = "🔗",
            label = "PARÁMS",
            value = formatBig(metrics.connections),
            color = DashGreen,
            progress = null
        )

        DashDivider()

        // Loss actual
        DashMetric(
            icon = "📉",
            label = "LOSS",
            value = String.format("%.4f", metrics.currentLoss),
            color = lossColor(metrics.currentLoss),
            progress = null
        )

        // Textos aprendidos
        DashMetric(
            icon = "📚",
            label = "TEXTOS",
            value = metrics.textsLearned.toString(),
            color = DashText,
            progress = null
        )

        // Eventos de crecimiento
        DashMetric(
            icon = "⚡",
            label = "CREC.",
            value = metrics.growthEvents.toString(),
            color = DashGold,
            progress = null
        )

        DashDivider()

        // Memoria semántica
        DashMetric(
            icon = "💾",
            label = "MEMORIA",
            value = metrics.semanticMemories.toString(),
            color = DashDim,
            progress = null
        )

        // Replay buffer
        DashMetric(
            icon = "🔄",
            label = "REPLAY",
            value = metrics.replayBufferSize.toString(),
            color = DashDim,
            progress = null
        )

        DashDivider()

        // Último tema aprendido
        DashLabel("📡 APRENDIENDO:")
        Text(
            text = metrics.lastTopic.ifEmpty { "Iniciando..." },
            color = DashAccent,
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
            maxLines = 3,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(top = 2.dp)
        )

        DashDivider()

        // Última actualización
        if (metrics.lastUpdate.isNotEmpty()) {
            DashLabel("🕐 ACTUALIZADO:")
            Text(
                text = metrics.lastUpdate,
                color = DashDim,
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace
            )
        }

        Spacer(modifier = Modifier.height(8.dp))
    }
}

// ─────────────────────────────────────────────
//  COMPONENTES INTERNOS
// ─────────────────────────────────────────────

@Composable
private fun DashHeader(isConnected: Boolean) {
    // Pulso de conexión
    val infiniteTransition = rememberInfiniteTransition(label = "conn")
    val pulse by infiniteTransition.animateFloat(
        initialValue = 0.4f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1000), RepeatMode.Reverse),
        label = "pulse"
    )

    Column {
        Text(
            text = "POLARIS",
            color = DashAccent,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 4.sp
        )
        Text(
            text = "NEURAL AI",
            color = DashDim,
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 2.sp
        )
        Spacer(modifier = Modifier.height(6.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Canvas(modifier = Modifier.size(8.dp)) {
                drawCircle(
                    color = if (isConnected) DashGreen.copy(alpha = pulse) else Color.Red,
                    radius = size.minDimension / 2f
                )
            }
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = if (isConnected) "ONLINE" else "OFFLINE",
                color = if (isConnected) DashGreen else Color.Red,
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace
            )
        }
    }
}

@Composable
private fun DashMetric(
    icon: String,
    label: String,
    value: String,
    color: Color,
    progress: Float?
) {
    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Row(
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(
                text = "$icon $label",
                color = DashDim,
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace
            )
        }
        Text(
            text = value,
            color = color,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace
        )
        if (progress != null) {
            // Barra de progreso
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(3.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(DashBorder)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .fillMaxWidth(progress)
                        .clip(RoundedCornerShape(2.dp))
                        .background(
                            Brush.horizontalGradient(listOf(color, color.copy(alpha = 0.5f)))
                        )
                )
            }
        }
    }
}

@Composable
private fun DashLabel(text: String) {
    Text(
        text = text,
        color = DashDim,
        fontSize = 9.sp,
        fontFamily = FontFamily.Monospace
    )
}

@Composable
private fun DashDivider() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(DashBorder)
    )
}

// ─────────────────────────────────────────────
//  UTILIDADES
// ─────────────────────────────────────────────

private fun formatBig(n: Int): String = when {
    n >= 1_000_000 -> String.format("%.1fM", n / 1_000_000f)
    n >= 1_000     -> String.format("%.1fK", n / 1_000f)
    else           -> n.toString()
}

private fun lossColor(loss: Float): Color = when {
    loss > 5f   -> Color(0xFFFF4444)   // Rojo — loss muy alta
    loss > 2f   -> Color(0xFFFFAA00)   // Naranja — loss moderada
    loss > 0.5f -> Color(0xFFFFFF00)   // Amarillo — aprendiendo
    else        -> Color(0xFF00FF88)   // Verde — loss baja
}
