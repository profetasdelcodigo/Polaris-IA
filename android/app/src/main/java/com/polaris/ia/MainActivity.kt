// Polaris IA — MainActivity
// Pantalla principal: red neuronal animada (izquierda) + dashboard (derecha)

package com.polaris.ia

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.unit.dp
import com.polaris.ia.ui.DashboardPanel
import com.polaris.ia.ui.NeuralNetworkGraph
import com.polaris.ia.viewmodel.PolarisViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: PolarisViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Pantalla completa sin barra de estado
        window.decorView.systemUiVisibility = (
            android.view.View.SYSTEM_UI_FLAG_FULLSCREEN or
            android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
            android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        )

        setContent {
            PolarisMainScreen(viewModel)
        }
    }
}

// ─────────────────────────────────────────────
//  PANTALLA PRINCIPAL
//  Layout: [Neural Graph 70%] | [Dashboard 30%]
// ─────────────────────────────────────────────

@Composable
fun PolarisMainScreen(viewModel: PolarisViewModel) {
    val animatedNeurons by viewModel.animatedNeurons.collectAsState()
    val connections     by viewModel.connections.collectAsState()
    val metrics         by viewModel.metrics.collectAsState()
    val progress        by viewModel.progress.collectAsState()
    val isConnected     by viewModel.isConnected.collectAsState()

    Row(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF050A14))  // Fondo negro azulado
    ) {
        // ── Visualización de la red neuronal (70% de la pantalla) ──
        NeuralNetworkGraph(
            animatedNeurons = animatedNeurons,
            connections = connections,
            modifier = Modifier
                .weight(0.70f)
                .fillMaxHeight()
                .onGloballyPositioned { coords ->
                    viewModel.canvasWidth = coords.size.width.toFloat()
                    viewModel.canvasHeight = coords.size.height.toFloat()
                }
        )

        // ── Separador vertical ──
        Box(
            modifier = Modifier
                .width(1.dp)
                .fillMaxHeight()
                .background(Color(0xFF1A3A6A))
        )

        // ── Dashboard de métricas (30% de la pantalla) ──
        DashboardPanel(
            metrics = metrics,
            progress = progress,
            isConnected = isConnected,
            modifier = Modifier
                .weight(0.30f)
                .fillMaxHeight()
        )
    }
}
