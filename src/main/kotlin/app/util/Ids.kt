package app.util

import com.github.slugify.Slugify
import org.apache.commons.codec.digest.DigestUtils
import java.util.Locale

object Ids {
    private val slugify = Slugify.builder().lowerCase(true).locale(Locale.ENGLISH).build()

    fun lessonId(title: String, unit: Int, lessonNumber: Int): String {
        val slug = slugify.slugify(title.ifBlank { "lesson" })
        return "mmspanish__grammar_%03d_%s".format(unit, slug)
    }

    fun vocabId(spanish: String, pos: String, gender: String?): String {
        val key = listOf(spanish.trim(), pos.trim(), gender?.trim() ?: "").joinToString("|")
        val hash = DigestUtils.sha256Hex(key.toByteArray()).lowercase(Locale.ENGLISH)
        return "mmspanish__vocab_${hash.substring(0, 16)}"
    }
}
