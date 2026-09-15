package com.example.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.R
import com.example.ui.theme.VibrantGreen

/**
 * A delightful, subtle animated checkmark badge shown when a download completes.
 * Features an initial bouncy scale pop, an expanding glow pulse ring, and a crisp checkmark.
 */
@Composable
fun AnimatedCompletionCheckmark(
    modifier: Modifier = Modifier,
    size: Dp = 18.dp,
    showLabel: Boolean = true,
    labelText: String? = null
) {
    val scaleAnim = remember { Animatable(0.2f) }
    val alphaAnim = remember { Animatable(0f) }
    val pathProgress = remember { Animatable(0f) }

    LaunchedEffect(Unit) {
        // Bounce pop effect
        alphaAnim.animateTo(1f, tween(150))
        scaleAnim.animateTo(
            targetValue = 1f,
            animationSpec = spring(
                dampingRatio = Spring.DampingRatioMediumBouncy,
                stiffness = Spring.StiffnessLow
            )
        )
        // Checkmark drawing stroke progress
        pathProgress.animateTo(
            targetValue = 1f,
            animationSpec = tween(durationMillis = 280, easing = FastOutSlowInEasing)
        )
    }

    // Subtle gentle pulse ring
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.25f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseScale"
    )
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.35f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseAlpha"
    )

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier.size(size),
            contentAlignment = Alignment.Center
        ) {
            // Expanding pulse halo
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .scale(pulseScale)
                    .clip(CircleShape)
                    .background(VibrantGreen.copy(alpha = pulseAlpha))
            )

            // Green background circle with bouncy entry
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .scale(scaleAnim.value)
                    .clip(CircleShape)
                    .background(VibrantGreen),
                contentAlignment = Alignment.Center
            ) {
                // Animated smooth checkmark path
                Canvas(modifier = Modifier.size(size * 0.55f)) {
                    val strokeWidth = 2.dp.toPx()
                    val path = Path().apply {
                        moveTo(x = size.toPx() * 0.12f, y = size.toPx() * 0.28f)
                        lineTo(x = size.toPx() * 0.24f, y = size.toPx() * 0.40f)
                        lineTo(x = size.toPx() * 0.45f, y = size.toPx() * 0.16f)
                    }
                    drawPath(
                        path = path,
                        color = Color.White,
                        style = Stroke(
                            width = strokeWidth,
                            cap = StrokeCap.Round,
                            join = StrokeJoin.Round
                        )
                    )
                }
            }
        }

        if (showLabel) {
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = labelText ?: stringResource(id = R.string.saved_to_gallery),
                fontSize = 11.sp,
                color = VibrantGreen,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}
