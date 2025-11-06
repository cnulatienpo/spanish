/// @function scr_mix_cefr_default_min(_cefr)
/// @description Provide default minimum Spanish tokens per CEFR stage.
/// @param {string} _cefr
function scr_mix_cefr_default_min(_cefr) {
    var c = string_upper(_cefr);
    if (c == "A0") return 1;
    if (c == "A1") return 2;
    if (c == "A2") return 3;
    if (c == "B1") return 5;
    if (c == "B2") return 7;
    if (c == "C1") return 10;
    if (c == "C2") return 12;
    return 2;
}
