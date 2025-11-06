/// @function scr_detect_register(_user)
/// @description Detect the register (tú, usted, slang, neutral) in the response.
/// @param {string} _user
function scr_detect_register(_user) {
    var t = scr_tokenize(_user);
    var mode = "neutral";
    for (var i = 0; i < array_length(t); i++) {
        var w = t[i];
        if (w == "usted" || w == "su" || w == "sus") {
            return "usted";
        }
        if (w == "tu" || w == "tú" || w == "te") {
            return "tú";
        }
        if (w == "wey" || w == "güey" || w == "vato" || w == "compa" || w == "bro") {
            return "slang";
        }
    }
    return mode;
}
