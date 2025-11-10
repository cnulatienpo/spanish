package app.validate

import app.model.Lesson
import app.model.Vocabulary
import app.util.JsonTools
import org.everit.json.schema.Schema
import org.everit.json.schema.ValidationException
import org.everit.json.schema.loader.SchemaLoader
import org.json.JSONObject

class Validator {
    private val lessonSchema: Schema = loadSchema("/schemas/lesson.schema.json")
    private val vocabSchema: Schema = loadSchema("/schemas/vocab.schema.json")

    data class ValidationResult<T>(val valid: List<T>, val invalid: List<Invalid<T>>)

    data class Invalid<T>(val item: T, val reason: String)

    fun validateLessons(items: List<Lesson>): ValidationResult<Lesson> {
        val valid = mutableListOf<Lesson>()
        val invalid = mutableListOf<Invalid<Lesson>>()
        for (item in items) {
            val json = JSONObject(JsonTools.mapper.writeValueAsString(item))
            try {
                lessonSchema.validate(json)
                valid.add(item)
            } catch (ex: ValidationException) {
                invalid.add(Invalid(item, ex.allMessages.joinToString("; ")))
            }
        }
        return ValidationResult(valid, invalid)
    }

    fun validateVocabulary(items: List<Vocabulary>): ValidationResult<Vocabulary> {
        val valid = mutableListOf<Vocabulary>()
        val invalid = mutableListOf<Invalid<Vocabulary>>()
        for (item in items) {
            val json = JSONObject(JsonTools.mapper.writeValueAsString(item))
            try {
                vocabSchema.validate(json)
                valid.add(item)
            } catch (ex: ValidationException) {
                invalid.add(Invalid(item, ex.allMessages.joinToString("; ")))
            }
        }
        return ValidationResult(valid, invalid)
    }

    private fun loadSchema(path: String): Schema {
        val resource = javaClass.getResourceAsStream(path) ?: error("Schema $path not found")
        resource.use { stream ->
            val raw = stream.readAllBytes().toString(Charsets.UTF_8)
            val json = JSONObject(raw)
            return SchemaLoader.load(json)
        }
    }
}
