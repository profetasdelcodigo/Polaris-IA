// Polaris IA — ViewModel
// Gestiona el estado de la IA y la comunicación con el servidor y Supabase Realtime

package com.polaris.ia.viewmodel

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.AnimationVector1D
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.polaris.ia.data.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlin.math.*
import kotlin.random.Random

// ─────────────────────────────────────────────
//  ESTADO DE UNA NEURONA CON ANIMACIONES
// ─────────────────────────────────────────────

class AnimatedNeuron(
    val neuron: Neuron,
    val scale: Animatable<Float, AnimationVector1D> = Animatable(0.3f),
    val glow: Animatable<Float, AnimationVector1D> = Animatable(0.2f)
)

// ─────────────────────────────────────────────
//  VIEWMODEL PRINCIPAL
// ─────────────────────────────────────────────

class PolarisViewModel : ViewModel() {

    // URL del servidor FastAPI (cambiar por la URL de Railway/Render en producción)
    private val serverUrl = "ws://10.0.2.2:8000/ws"   // 10.0.2.2 = localhost en emulador Android
    private val metricsUrl = "http://10.0.2.2:8000/metrics"

    // ── Estado observable ─────────────────────

    private val _animatedNeurons = MutableStateFlow<List<AnimatedNeuron>>(emptyList())
    val animatedNeurons: StateFlow<List<AnimatedNeuron>> = _animatedNeurons.asStateFlow()

    private val _connections = MutableStateFlow<List<Connection>>(emptyList())
    val connections: StateFlow<List<Connection>> = _connections.asStateFlow()

    private val _metrics = MutableStateFlow(LearningMetrics())
    val metrics: StateFlow<LearningMetrics> = _metrics.asStateFlow()

    private val _statusMessage = MutableStateFlow("Conectando con Polaris IA...")
    val statusMessage: StateFlow<String> = _statusMessage.asStateFlow()

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()

    // ── Dimensiones del canvas (se actualizan desde la UI) ────
    var canvasWidth: Float = 1080f
    var canvasHeight: Float = 1920f

    init {
        startPolling()
    }

    // ─────────────────────────────────────────
    //  POLLING A LA API (cada 5 segundos)
    //  Fallback simple que no requiere WebSocket
    // ─────────────────────────────────────────

    private fun startPolling() {
        viewModelScope.launch {
            while (true) {
                try {
                    fetchMetrics()
                    _isConnected.value = true
                } catch (e: Exception) {
                    _isConnected.value = false
                    _statusMessage.value = "Reconectando..."
                }
                delay(5_000)
            }
        }
    }

    private suspend fun fetchMetrics() {
        // Usar HttpURLConnection simple (sin dependencias extra)
        val result = withContext(Dispatchers.IO) {
            try {
                val url = java.net.URL(metricsUrl)
                val conn = url.openConnection() as java.net.HttpURLConnection
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                val response = conn.inputStream.bufferedReader().readText()
                conn.disconnect()
                response
            } catch (e: Exception) {
                null
            }
        }

        result?.let { json ->
            parseAndUpdateMetrics(json)
        }
    }

    // ─────────────────────────────────────────
    //  PARSEO DE RESPUESTA JSON (manual, sin Gson)
    // ─────────────────────────────────────────

    private fun parseAndUpdateMetrics(json: String) {
        try {
            val neurons = extractInt(json, "neurons") ?: return
            val connections = extractInt(json, "connections") ?: 0
            val loss = extractFloat(json, "loss") ?: 0f
            val texts = extractInt(json, "texts_learned") ?: 0
            val growth = extractInt(json, "growth_events") ?: 0
            val topic = extractString(json, "last_topic") ?: "Aprendiendo..."

            val newMetrics = LearningMetrics(
                neurons = neurons,
                connections = connections,
                currentLoss = loss,
                textsLearned = texts,
                growthEvents = growth,
                lastTopic = topic,
                lastUpdate = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
                    .format(java.util.Date())
            )

            val currentCount = _animatedNeurons.value.size
            if (neurons != currentCount) {
                updateNeuronVisualization(neurons, connections)
            }

            _metrics.value = newMetrics
            _statusMessage.value = "🧠 Polaris IA activa — ${neurons} neuronas"

        } catch (e: Exception) {
            // Ignorar errores de parseo
        }
    }

    // ─────────────────────────────────────────
    //  ACTUALIZAR VISUALIZACIÓN DE LA RED
    // ─────────────────────────────────────────

    private fun updateNeuronVisualization(targetNeurons: Int, targetConnections: Int) {
        viewModelScope.launch {
            val current = _animatedNeurons.value.toMutableList()
            val currentCount = current.size

            if (targetNeurons > currentCount) {
                // Añadir nuevas neuronas con animación de pulso
                val newNeurons = mutableListOf<AnimatedNeuron>()

                repeat(targetNeurons - currentCount) { i ->
                    val idx = currentCount + i
                    val position = calculateNeuronPosition(idx, targetNeurons)

                    val animNeuron = AnimatedNeuron(
                        neuron = Neuron(
                            id = "N$idx",
                            x = position.first,
                            y = position.second,
                            layer = idx / maxOf(1, targetNeurons / 4),
                            status = NeuronStatus.NEW
                        )
                    )
                    newNeurons.add(animNeuron)
                }

                current.addAll(newNeurons)
                _animatedNeurons.value = current.toList()

                // Animar aparición de las nuevas neuronas
                newNeurons.forEach { animNeuron ->
                    launch {
                        // Pulso de entrada: crece rápido y luego estabiliza
                        animNeuron.scale.animateTo(1.8f,
                            androidx.compose.animation.core.tween(300))
                        animNeuron.scale.animateTo(1.0f,
                            androidx.compose.animation.core.tween(200))
                        animNeuron.glow.animateTo(0.9f,
                            androidx.compose.animation.core.tween(200))
                        animNeuron.glow.animateTo(0.4f,
                            androidx.compose.animation.core.tween(500))
                    }
                }
            }

            // Actualizar conexiones
            val newConnections = generateConnections(
                _animatedNeurons.value.map { it.neuron },
                targetConnections
            )
            _connections.value = newConnections

            // Activar algunas neuronas aleatoriamente para efecto visual
            activateRandomNeurons()
        }
    }

    private fun calculateNeuronPosition(index: Int, total: Int): Pair<Float, Float> {
        // Layout en espiral para que se vea dinámico y orgánico
        val angle = index * 137.5f * (Math.PI / 180f)  // Ángulo áureo
        val radius = 60f + (index * 18f)
        val centerX = canvasWidth / 2f
        val centerY = canvasHeight * 0.45f

        val x = (centerX + radius * cos(angle)).toFloat()
            .coerceIn(40f, canvasWidth - 40f)
        val y = (centerY + radius * sin(angle)).toFloat()
            .coerceIn(40f, canvasHeight * 0.85f)

        return Pair(x, y)
    }

    private fun generateConnections(neurons: List<Neuron>, maxConnections: Int): List<Connection> {
        if (neurons.size < 2) return emptyList()
        val connections = mutableListOf<Connection>()
        val limit = minOf(maxConnections / 10, neurons.size * 3, 500)

        repeat(limit) {
            val fromIdx = Random.nextInt(neurons.size)
            val toIdx = Random.nextInt(neurons.size)
            if (fromIdx != toIdx) {
                connections.add(
                    Connection(
                        fromId = neurons[fromIdx].id,
                        toId = neurons[toIdx].id,
                        strength = Random.nextFloat() * 0.8f + 0.2f
                    )
                )
            }
        }
        return connections
    }

    private fun activateRandomNeurons() {
        viewModelScope.launch {
            val neurons = _animatedNeurons.value
            if (neurons.isEmpty()) return@launch

            // Activar 3 neuronas aleatorias con un pulso
            repeat(3) {
                val idx = Random.nextInt(neurons.size)
                launch {
                    neurons[idx].glow.animateTo(1.0f,
                        androidx.compose.animation.core.tween(200))
                    delay(300)
                    neurons[idx].glow.animateTo(0.3f,
                        androidx.compose.animation.core.tween(600))
                }
            }
        }
    }

    // ─────────────────────────────────────────
    //  PARSEO JSON MANUAL (sin dependencias)
    // ─────────────────────────────────────────

    private fun extractInt(json: String, key: String): Int? {
        val regex = Regex(""""$key"\s*:\s*(\d+)""")
        return regex.find(json)?.groupValues?.get(1)?.toIntOrNull()
    }

    private fun extractFloat(json: String, key: String): Float? {
        val regex = Regex(""""$key"\s*:\s*([\d.]+)""")
        return regex.find(json)?.groupValues?.get(1)?.toFloatOrNull()
    }

    private fun extractString(json: String, key: String): String? {
        val regex = Regex(""""$key"\s*:\s*"([^"]*?)"""")
        return regex.find(json)?.groupValues?.get(1)
    }
}
