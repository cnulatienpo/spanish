/// @function scr_seeder_cefr_ok(_c)
/// @description Return true if the provided CEFR string is valid (A0..C2).
/// @param _c
function scr_seeder_cefr_ok(_c) {
    var C = string_upper(string(_c));
    return (C == "A0" || C == "A1" || C == "A2" || C == "B1" || C == "B2" || C == "C1" || C == "C2");
}
