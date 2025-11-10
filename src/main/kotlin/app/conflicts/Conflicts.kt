package app.conflicts

import app.merge.DeepMerge
import app.merge.MergeContext
import app.normalize.Normalizer
import com.fasterxml.jackson.databind.JsonNode
import org.slf4j.LoggerFactory
import java.nio.file.Path

class ConflictResolver(private val normalizer: Normalizer) {
    private val logger = LoggerFactory.getLogger(ConflictResolver::class.java)
    private val regex = Regex("(?s)<<<<<<<.*?\n(.*?)\n=======\n(.*?)\n>>>>>>>.*?\n?")

    data class Result(val healedText: String, val healedCount: Int, val rejects: List<Reject>)

    data class Reject(val source: Path, val reason: String, val fragment: String)

    fun healConflicts(input: String, path: Path, mtime: Long): Result {
        val rejects = mutableListOf<Reject>()
        var healedText = input
        var healedCount = 0
        regex.findAll(input).forEach { matchResult ->
            val leftText = matchResult.groupValues[1]
            val rightText = matchResult.groupValues[2]
            val replacement = resolveBlock(leftText, rightText, path, mtime)
            if (replacement == null) {
                rejects.add(Reject(path, "Unresolved conflict block", matchResult.value))
            } else {
                healedCount += 1
                healedText = healedText.replace(matchResult.value, replacement)
            }
        }
        return Result(healedText, healedCount, rejects)
    }

    private fun resolveBlock(left: String, right: String, path: Path, mtime: Long): String? {
        val leftNode = parseVariant(left)
        val rightNode = parseVariant(right)
        if (leftNode == null && rightNode == null) {
            logger.warn("Failed to parse conflict variants in {}", path)
            return null
        }
        if (leftNode == null) return rightNode!!.toString()
        if (rightNode == null) return leftNode.toString()
        val merged = DeepMerge.merge(leftNode, rightNode, MergeContext(mtime, mtime))
        return merged.toString()
    }

    private fun parseVariant(text: String): JsonNode? {
        val fragments = normalizer.tryParse(text)
        return fragments.firstOrNull()
    }
}
