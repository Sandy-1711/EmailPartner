package expo.modules.echowidget

import android.graphics.Color

/** Echo Mail tone palette, mirrored from src/tones.ts. Colors as ARGB ints. */
data class Palette(
  val base: Int,
  val blobs: IntArray,
  val accent: Int,
  val dot: Int,
)

object Palettes {
  private fun c(hex: String) = Color.parseColor(hex)

  private val TONES: Map<String, Palette> = mapOf(
    "urgent" to Palette(
      base = c("#0c0510"),
      blobs = intArrayOf(c("#7c3aed"), c("#c026d3"), c("#5b21b6"), c("#4338ca")),
      accent = c("#f0d6ff"), dot = c("#e879f9"),
    ),
    "social" to Palette(
      base = c("#041018"),
      blobs = intArrayOf(c("#2563eb"), c("#06b6d4"), c("#0ea5e9"), c("#1d4ed8")),
      accent = c("#cffafe"), dot = c("#38e1d6"),
    ),
    "informative" to Palette(
      base = c("#080b18"),
      blobs = intArrayOf(c("#4f5bd5"), c("#6366f1"), c("#3730a3"), c("#4f46e5")),
      accent = c("#dde3ff"), dot = c("#8c95ff"),
    ),
    "transactional" to Palette(
      base = c("#070914"),
      blobs = intArrayOf(c("#6366f1"), c("#818cf8"), c("#4338ca"), c("#5b6ee0")),
      accent = c("#e3e8ff"), dot = c("#a5b0ff"),
    ),
    "promotional" to Palette(
      base = c("#0a0716"),
      blobs = intArrayOf(c("#8b5cf6"), c("#a855f7"), c("#4c1d95"), c("#6d28d9")),
      accent = c("#ecdcff"), dot = c("#c084fc"),
    ),
  )

  fun forTone(tone: String?): Palette = TONES[tone] ?: TONES.getValue("informative")
}
