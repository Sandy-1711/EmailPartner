package expo.modules.echowidget

import android.graphics.Bitmap
import android.graphics.BlurMaskFilter
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RadialGradient
import android.graphics.RectF
import android.graphics.Shader
import kotlin.math.PI
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * Draws the widget visuals as bitmaps in the widget process — real native
 * Canvas, so the mesh gets a TRUE gaussian blur (BlurMaskFilter), not the SVG
 * fake. Mirrors the in-app MeshGradient / WavePlayer look.
 */
object MeshRenderer {
  // blob layout from src/widget/meshSvg.ts, in its 320x150 design space
  private const val DW = 320f
  private const val DH = 150f
  private val BLOBS = arrayOf(
    floatArrayOf(54f, 28f, 120f, 0f),
    floatArrayOf(270f, 40f, 116f, 1f),
    floatArrayOf(68f, 150f, 124f, 2f),
    floatArrayOf(292f, 150f, 132f, 3f),
  )

  fun mesh(palette: Palette, w: Int, h: Int): Bitmap {
    val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bmp)
    val sx = w / DW
    val sy = h / DH
    val corner = 24f * (w / DW)

    // rounded clip — corners stay transparent so the card reads as rounded
    val clip = Path().apply {
      addRoundRect(RectF(0f, 0f, w.toFloat(), h.toFloat()), corner, corner, Path.Direction.CW)
    }
    canvas.save()
    canvas.clipPath(clip)

    canvas.drawColor(palette.base)

    val blur = BlurMaskFilter(max(8f, w * 0.06f), BlurMaskFilter.Blur.NORMAL)
    for (b in BLOBS) {
      val cx = b[0] * sx
      val cy = b[1] * sy
      val r = b[2] * sx
      val color = palette.blobs[b[3].toInt()]
      val paint = Paint(Paint.ANTI_ALIAS_FLAG)
      paint.shader = RadialGradient(
        cx, cy, r,
        intArrayOf(withAlpha(color, 0.9f), withAlpha(color, 0.35f), withAlpha(color, 0f)),
        floatArrayOf(0f, 0.5f, 1f),
        Shader.TileMode.CLAMP,
      )
      paint.maskFilter = blur
      canvas.drawCircle(cx, cy, r, paint)
    }

    // top-left sheen for depth
    val sheen = Paint(Paint.ANTI_ALIAS_FLAG)
    sheen.shader = RadialGradient(
      w * 0.28f, h * 0.1f, w * 0.6f,
      intArrayOf(withAlpha(Color.WHITE, 0.10f), withAlpha(Color.WHITE, 0.03f), withAlpha(Color.WHITE, 0f)),
      floatArrayOf(0f, 0.55f, 1f),
      Shader.TileMode.CLAMP,
    )
    canvas.drawRect(0f, 0f, w.toFloat(), h.toFloat(), sheen)

    // readability veil, darker toward the bottom where the text sits
    val veil = Paint()
    veil.shader = LinearGradient(
      0f, 0f, 0f, h.toFloat(),
      intArrayOf(withAlpha(Color.BLACK, 0.04f), withAlpha(Color.BLACK, 0.12f), withAlpha(Color.BLACK, 0.5f)),
      floatArrayOf(0f, 0.4f, 1f),
      Shader.TileMode.CLAMP,
    )
    canvas.drawRect(0f, 0f, w.toFloat(), h.toFloat(), veil)

    canvas.restore()

    // lit inner border
    val stroke = Paint(Paint.ANTI_ALIAS_FLAG)
    stroke.style = Paint.Style.STROKE
    stroke.strokeWidth = max(1f, w * 0.004f)
    stroke.color = withAlpha(Color.WHITE, 0.1f)
    val inset = stroke.strokeWidth / 2f
    canvas.drawRoundRect(
      RectF(inset, inset, w - inset, h - inset), corner, corner, stroke
    )
    return bmp
  }

  /** Glowing tone dot. */
  fun dot(palette: Palette, size: Int = 42): Bitmap {
    val bmp = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bmp)
    val c = size / 2f
    val glow = Paint(Paint.ANTI_ALIAS_FLAG)
    glow.shader = RadialGradient(
      c, c, c,
      intArrayOf(withAlpha(palette.dot, 0.55f), withAlpha(palette.dot, 0f)),
      floatArrayOf(0.2f, 1f),
      Shader.TileMode.CLAMP,
    )
    canvas.drawCircle(c, c, c, glow)
    val core = Paint(Paint.ANTI_ALIAS_FLAG)
    core.color = palette.dot
    canvas.drawCircle(c, c, size * 0.18f, core)
    return bmp
  }

  /** Accent circle with a play triangle or a stop square. */
  fun playIcon(palette: Palette, playing: Boolean, size: Int = 72): Bitmap {
    val bmp = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bmp)
    val c = size / 2f
    val bg = Paint(Paint.ANTI_ALIAS_FLAG)
    bg.color = palette.accent
    canvas.drawCircle(c, c, c, bg)
    val glyph = Paint(Paint.ANTI_ALIAS_FLAG)
    glyph.color = Color.parseColor("#0a0612")
    if (playing) {
      val s = size * 0.28f
      canvas.drawRect(c - s, c - s, c + s, c + s, glyph)
    } else {
      val p = Path()
      val s = size * 0.3f
      p.moveTo(c - s * 0.8f, c - s)
      p.lineTo(c - s * 0.8f, c + s)
      p.lineTo(c + s, c)
      p.close()
      canvas.drawPath(p, glyph)
    }
    return bmp
  }

  /** Deterministic mini waveform; accent while playing, dim otherwise. */
  fun wave(id: String, playing: Boolean, palette: Palette, bars: Int = 9): Bitmap {
    val w = bars * 18
    val h = 60
    val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bmp)
    val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    paint.color = if (playing) palette.accent else withAlpha(Color.WHITE, 0.3f)
    val values = makeWave(id, bars)
    val barW = w * 0.5f / bars
    val gap = (w.toFloat() - barW * bars) / bars
    var x = gap / 2f
    for (v in values) {
      val bh = max(6f, v * h)
      val top = (h - bh) / 2f
      canvas.drawRoundRect(RectF(x, top, x + barW, top + bh), barW / 2f, barW / 2f, paint)
      x += barW + gap
    }
    return bmp
  }

  // mirrors makeWave() in src/components/WavePlayer.tsx (Long math, no overflow)
  private fun makeWave(id: String, n: Int): FloatArray {
    var h = 0L
    for (ch in id) h = (h * 31 + ch.code) % 233280L
    var s = (h + 3L) * 9301L + 49297L
    val out = FloatArray(n)
    for (i in 0 until n) {
      s = (s * 9301L + 49297L) % 233280L
      val r = s / 233280.0
      val env = 0.55 + 0.45 * sin((i.toDouble() / n) * PI)
      out[i] = min(1.0, max(0.18, env * (0.45 + r * 0.7))).toFloat()
    }
    return out
  }

  private fun withAlpha(color: Int, alpha: Float): Int =
    Color.argb((alpha * 255).toInt(), Color.red(color), Color.green(color), Color.blue(color))
}
