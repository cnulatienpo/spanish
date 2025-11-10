package app.parse

class Extractor {
    fun extract(jsonText: String): List<String> {
        val fragments = mutableListOf<String>()
        var depth = 0
        var start = -1
        var inString = false
        var escape = false
        for (i in jsonText.indices) {
            val ch = jsonText[i]
            if (escape) {
                escape = false
                continue
            }
            when (ch) {
                '\\' -> if (inString) escape = true
                '"' -> inString = !inString
                '{', '[' -> if (!inString) {
                    if (depth == 0) {
                        start = i
                    }
                    depth += 1
                }
                '}', ']' -> if (!inString && depth > 0) {
                    depth -= 1
                    if (depth == 0 && start >= 0) {
                        fragments.add(jsonText.substring(start, i + 1))
                        start = -1
                    }
                }
            }
        }
        if (fragments.isEmpty()) {
            val trimmed = jsonText.trim()
            if (trimmed.isNotEmpty()) {
                fragments.add(trimmed)
            }
        }
        return fragments
    }
}
