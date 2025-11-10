package app.audit

import java.time.Duration
import java.time.Instant

class Audit {
    data class Summary(
        val filesScanned: Int,
        val conflictsHealed: Int,
        val parsedFragments: Int,
        val lessons: Int,
        val vocabulary: Int,
        val duplicateClusters: Int,
        val unsetLevelIds: List<String>,
        val rejects: Int,
        val rejectDetails: List<String>,
        val duration: Duration
    )

    fun render(summary: Summary): String {
        val builder = StringBuilder()
        builder.appendLine("🔍 Scanned ${summary.filesScanned} files")
        builder.appendLine("⚔️  Healed ${summary.conflictsHealed} conflict blocks")
        builder.appendLine("🧩  Parsed ${summary.parsedFragments} fragments")
        builder.appendLine("📚  ${summary.vocabulary} vocab | ${summary.lessons} lessons")
        builder.appendLine("✅  ${summary.duplicateClusters} duplicate clusters merged")
        builder.appendLine("⚠️  ${summary.unsetLevelIds.size} items with UNSET level")
        builder.appendLine("🚫  ${summary.rejects} rejects saved")
        builder.appendLine("⏱️  Duration: ${summary.duration.toMillis()} ms")
        if (summary.unsetLevelIds.isNotEmpty()) {
            builder.appendLine().appendLine("## UNSET level items")
            summary.unsetLevelIds.sorted().forEach { builder.appendLine("- $it") }
        }
        if (summary.rejectDetails.isNotEmpty()) {
            builder.appendLine().appendLine("## Rejects")
            summary.rejectDetails.forEach { builder.appendLine("- $it") }
        }
        return builder.toString()
    }
}
