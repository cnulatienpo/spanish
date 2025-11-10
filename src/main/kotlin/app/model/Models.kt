package app.model

data class LessonStep(
    val phase: String,
    val line: String? = null,
    val origin: String? = null,
    val story: String? = null,
    val items: List<String>? = null
)

data class Lesson(
    val id: String,
    val title: String,
    val nickname: String,
    val level: String,
    val unit: Int,
    val lesson_number: Int,
    val tags: List<String>,
    val steps: List<LessonStep>,
    val notes: String? = null,
    val source_files: List<String>
) {
    fun sortKey(): Triple<Int, Int, String> {
        val rank = cefrRank(level)
        val unitVal = unit.takeIf { it >= 0 } ?: 9999
        val lessonVal = lesson_number.takeIf { it >= 0 } ?: 9999
        val combined = unitVal * 10000 + lessonVal
        return Triple(rank, combined, id)
    }
}

data class Example(
    val es: String,
    val en: String
)

data class Vocabulary(
    val id: String,
    val spanish: String,
    val pos: String,
    val english_gloss: String,
    val definition: String,
    val origin: String? = null,
    val story: String? = null,
    val gender: String? = null,
    val examples: List<Example>,
    val level: String,
    val tags: List<String>,
    val source_files: List<String>,
    val notes: String? = null
) {
    fun sortKey(): Triple<Int, Int, String> {
        val rank = cefrRank(level)
        return Triple(rank, 0, id)
    }
}

fun cefrRank(level: String): Int = when (level.uppercase()) {
    "A1" -> 1
    "A2" -> 2
    "B1" -> 3
    "B2" -> 4
    "C1" -> 5
    "C2" -> 6
    else -> 7
}
