/// @function scr_register_examples(_expected)
/// @description Provide short example starters for a given register.
/// @param {string} _expected
function scr_register_examples(_expected) {
    var r = string_lower(string(_expected));
    if (r == "tu" || r == "tú") {
        return [
            "¿Cómo te llamas?",
            "¿Puedes ayudarme con...?",
            "Te recomiendo que...",
            "¿Me dices dónde...?",
            "¿Quieres probar...?"
        ];
    } else if (r == "usted") {
        return [
            "¿Podría indicarme...?",
            "Permítame explicar...",
            "¿Le parece bien si...?",
            "Quisiera pedirle...",
            "Con todo respeto,"
        ];
    } else if (r == "slang") {
        return [
            "La neta,",
            "Órale,",
            "Con todo respeto,",
            "Cámara,",
            "Pues la pura verdad,"
        ];
    } else {
        return [
            "Disculpa,",
            "Por favor,",
            "Yo pienso que...",
            "Creo que...",
            "Entonces,"
        ];
    }
}
