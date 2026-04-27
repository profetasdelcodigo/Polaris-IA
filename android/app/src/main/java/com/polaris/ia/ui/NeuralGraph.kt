// Polaris IA — Neural Graph Canvas
// Visualización sci-fi de la red neuronal con efectos de glow y partículas

package com.polaris.ia.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.polaris.ia.data.*
import com.polaris.ia.viewmodel.AnimatedNeuron
import kotlin.math.*

// ─────────────────────────────────────────────
//  COLORES SCI-FI
// ─────────────────────────────────────────────

private val ColorBg        = Color(0xFF050A14)    // Fondo negro azulado
private val ColorIdle      = Color(0xFF1A4A8A)    // Azul oscuro — inactiva
private val ColorLearning  = Color(0xFF00FF88)    // Verde neón — aprendiendo
private val ColorActive    = Color(0xFFFFFFFF)    // Blanco puro — muy activa
private val ColorNew       = Color(0xFF00DDFF)    // Cyan — recién creada
private val ColorConnLine  = Color(0xFF1E4080)    // Azul líneas de conexión
private val ColorParticle  = Color(0xFF00AAFF)    // Partícula fluyendo

// ─────────────────────────────────────────────
//  COMPONENTE PRINCIPAL
// ─────────────────────────────────────────────

@Composable
fun NeuralNetworkGraph(
    animatedNeurons: List<AnimatedNeuron>,
    connections: List<Connection>,
    modifier: Modifier = Modifier
) {
    // Animación infinita de partículas en las conexiones
    val infiniteTransition = rememberInfiniteTransition(label = "particles")
    val particleOffset by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "particleOffset"
    )

    // Pulso global suave para neuronas inactivas
    val globalPulse by infiniteTransition.animateFloat(
        initialValue = 0.7f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "globalPulse"
    )

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(ColorBg)
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            // 1. Fondo — grid sutil de puntos
            drawBackgroundGrid()

            // 2. Mapa de neuronas por ID para buscar posiciones rápido
            val neuronMap = animatedNeurons.associate { it.neuron.id to it.neuron }

            // 3. Dibujar conexiones
            connections.forEach { conn ->
                val from = neuronMap[conn.fromId] ?: return@forEach
                val to = neuronMap[conn.toId] ?: return@forEach
                drawConnection(from, to, conn.strength, particleOffset)
            }

            // 4. Dibujar neuronas
            animatedNeurons.forEach { animNeuron ->
                val neuron = animNeuron.neuron
                val scale = animNeuron.scale.value
                val glow = animNeuron.glow.value

                drawNeuron(neuron, scale, glow, globalPulse)
            }
        }
    }
}

// ─────────────────────────────────────────────
//  DIBUJAR FONDO GRID
// ─────────────────────────────────────────────

private fun DrawScope.drawBackgroundGrid() {
    val gridColor = Color(0xFF0A1628).copy(alpha = 0.6f)
    val step = 60f

    var x = 0f
    while (x < size.width) {
        drawLine(gridColor, Offset(x, 0f), Offset(x, size.height), strokeWidth = 0.5f)
        x += step
    }
    var y = 0f
    while (y < size.height) {
        drawLine(gridColor, Offset(0f, y), Offset(size.width, y), strokeWidth = 0.5f)
        y += step
    }
}

// ─────────────────────────────────────────────
//  DIBUJAR CONEXIÓN CON PARTÍCULA
// ─────────────────────────────────────────────

private fun DrawScope.drawConnection(
    from: Neuron,
    to: Neuron,
    strength: Float,
    particleT: Float
) {
    val startOffset = Offset(from.x, from.y)
    val endOffset = Offset(to.x, to.y)

    // Línea base (tenue)
    drawLine(
        color = ColorConnLine.copy(alpha = 0.15f + strength * 0.2f),
        start = startOffset,
        end = endOffset,
        strokeWidth = 0.8f + strength * 1.5f,
        cap = StrokeCap.Round
    )

    // Partícula que fluye por la línea
    val px = from.x + (to.x - from.x) * particleT
    val py = from.y + (to.y - from.y) * particleT

    // Glow de la partícula
    drawCircle(
        color = ColorParticle.copy(alpha = 0.4f),
        radius = 5f,
        center = Offset(px, py)
    )
    // Núcleo brillante
    drawCircle(
        color = Color.White.copy(alpha = 0.8f),
        radius = 2f,
        center = Offset(px, py)
    )
}

// ─────────────────────────────────────────────
//  DIBUJAR NEURONA CON GLOW
// ─────────────────────────────────────────────

private fun DrawScope.drawNeuron(
    neuron: Neuron,
    scale: Float,
    glow: Float,
    globalPulse: Float
) {
    val center = Offset(neuron.x, neuron.y)

    // Color según estado
    val coreColor = when (neuron.status) {
        NeuronStatus.IDLE     -> ColorIdle
        NeuronStatus.LEARNING -> ColorLearning
        NeuronStatus.ACTIVE   -> ColorActive
        NeuronStatus.NEW      -> ColorNew
    }

    val glowColor = when (neuron.status) {
        NeuronStatus.IDLE     -> Color(0xFF0055AA)
        NeuronStatus.LEARNING -> Color(0xFF00FF66)
        NeuronStatus.ACTIVE   -> Color(0xFFCCDDFF)
        NeuronStatus.NEW      -> Color(0xFF00CCFF)
    }

    val baseRadius = 12f * scale
    val effectivePulse = if (neuron.status == NeuronStatus.IDLE) globalPulse else 1f

    // Halo exterior (glow grande)
    drawCircle(
        brush = Brush.radialGradient(
            colors = listOf(
                glowColor.copy(alpha = glow * 0.5f * effectivePulse),
                Color.Transparent
            ),
            center = center,
            radius = baseRadius * 3.5f
        ),
        radius = baseRadius * 3.5f,
        center = center
    )

    // Anillo intermedio
    drawCircle(
        color = glowColor.copy(alpha = glow * 0.7f),
        radius = baseRadius * 1.8f,
        center = center,
        style = Stroke(width = 1.5f)
    )

    // Núcleo de la neurona (relleno sólido)
    drawCircle(
        brush = Brush.radialGradient(
            colors = listOf(
                Color.White.copy(alpha = 0.9f),
                coreColor
            ),
            center = center,
            radius = baseRadius
        ),
        radius = baseRadius,
        center = center
    )
}
