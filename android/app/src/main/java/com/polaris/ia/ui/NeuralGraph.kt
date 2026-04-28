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
    // Estado para zoom y pan
    var scale by remember { mutableFloatStateOf(1f) }
    var offset by remember { mutableStateOf(Offset.Zero) }

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

    val globalPulse by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(2500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "globalPulse"
    )

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(ColorBg)
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, zoom, _ ->
                    scale = (scale * zoom).coerceIn(0.5f, 5f)
                    offset += pan
                }
            }
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            // Aplicar transformación de cámara
            withTransform({
                translate(offset.x, offset.y)
                scale(scale, scale, Offset(size.width / 2, size.height / 2))
            }) {
                drawBackgroundGrid()

                val neuronMap = animatedNeurons.associateBy { it.neuron.id }

                // Dibujar conexiones primero (atrás)
                connections.forEach { conn ->
                    val from = neuronMap[conn.fromId]?.neuron ?: return@forEach
                    val to = neuronMap[conn.toId]?.neuron ?: return@forEach
                    drawConnection(from, to, conn.strength, particleOffset)
                }

                // Dibujar neuronas
                animatedNeurons.forEach { animNeuron ->
                    drawNeuron(
                        animNeuron.neuron,
                        animNeuron.scale.value,
                        animNeuron.glow.value,
                        globalPulse
                    )
                }
            }
        }
    }
}

// ─────────────────────────────────────────────
//  DIBUJAR FONDO GRID (MEJORADO)
// ─────────────────────────────────────────────

private fun DrawScope.drawBackgroundGrid() {
    val gridColor = Color(0xFF00DDFF).copy(alpha = 0.05f)
    val step = 80f
    
    // Dibujar líneas verticales y horizontales infinitas (basadas en viewport)
    var x = -5000f
    while (x < 5000f) {
        drawLine(gridColor, Offset(x, -5000f), Offset(x, 5000f), strokeWidth = 1f)
        x += step
    }
    var y = -5000f
    while (y < 5000f) {
        drawLine(gridColor, Offset(-5000f, y), Offset(5000f, y), strokeWidth = 1f)
        y += step
    }
}

// ─────────────────────────────────────────────
//  DIBUJAR CONEXIÓN (CON COLORES SEGÚN LÓBULO)
// ─────────────────────────────────────────────

private fun DrawScope.drawConnection(
    from: Neuron,
    to: Neuron,
    strength: Float,
    particleT: Float
) {
    val start = Offset(from.x, from.y)
    val end = Offset(to.x, to.y)
    
    // El color depende del hemisferio (par = Cyan, impar = Púrpura)
    val baseColor = if (from.id % 2 == 0) ColorNew else Color(0xFFBB44FF)

    drawLine(
        brush = Brush.linearGradient(
            colors = listOf(baseColor.copy(alpha = 0.1f), baseColor.copy(alpha = 0.4f)),
            start = start,
            end = end
        ),
        start = start,
        end = end,
        strokeWidth = 1f + strength * 2f,
        cap = StrokeCap.Round
    )

    // Partícula
    val px = from.x + (to.x - from.x) * particleT
    val py = from.y + (to.y - from.y) * particleT
    
    drawCircle(
        color = Color.White.copy(alpha = 0.6f),
        radius = 2.5f,
        center = Offset(px, py)
    )
}

// ─────────────────────────────────────────────
//  DIBUJAR NEURONA (PREMIUM GLOW)
// ─────────────────────────────────────────────

private fun DrawScope.drawNeuron(
    neuron: Neuron,
    scale: Float,
    glow: Float,
    globalPulse: Float
) {
    val center = Offset(neuron.x, neuron.y)
    val isLeft = neuron.id % 2 == 0
    
    val baseColor = if (isLeft) ColorNew else Color(0xFFBB44FF)
    val coreColor = when (neuron.status) {
        NeuronStatus.IDLE     -> baseColor.copy(alpha = 0.6f)
        NeuronStatus.LEARNING -> ColorLearning
        NeuronStatus.ACTIVE   -> ColorActive
        NeuronStatus.NEW      -> ColorNew
    }

    val radius = 14f * scale * (if (neuron.status == NeuronStatus.IDLE) globalPulse else 1.1f)

    // Glow Exterior
    drawCircle(
        brush = Brush.radialGradient(
            0.0f to coreColor.copy(alpha = 0.5f * glow),
            1.0f to Color.Transparent,
            center = center,
            radius = radius * 4f
        ),
        radius = radius * 4f,
        center = center
    )

    // Borde Neón
    drawCircle(
        color = coreColor,
        radius = radius,
        center = center,
        style = Stroke(width = 2f)
    )

    // Núcleo Brillante
    drawCircle(
        brush = Brush.radialGradient(
            0.0f to Color.White,
            0.4f to coreColor,
            1.0f to coreColor.copy(alpha = 0.2f),
            center = center,
            radius = radius
        ),
        radius = radius * 0.8f,
        center = center
    )
}
