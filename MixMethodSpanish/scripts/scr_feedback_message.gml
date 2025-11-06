/// @function scr_feedback_message(_score)
/// @description Build a conversational feedback string for the player.
/// @param {ds_map} _score
function scr_feedback_message(_score) {
    var msg = "";
    var pass = false;
    if (ds_map_exists(_score, "pass")) {
        pass = ds_map_find_value(_score, "pass");
    }
    if (!pass) {
        var need = 0;
        if (ds_map_exists(_score, "need")) {
            need = ds_map_find_value(_score, "need");
        }
        if (need > 0) {
            msg = "Add " + string(need) + " more Spanish palabra(s)!";
        } else {
            msg = "Try mixing one in, bro!";
        }
    } else {
        var r = 0;
        if (ds_map_exists(_score, "register_bonus")) {
            r = ds_map_find_value(_score, "register_bonus");
        }
        if (r > 0) {
            msg = "🔥 Nailed the register! Bonus for style.";
        } else {
            var ratio = 0;
            if (ds_map_exists(_score, "ratio")) {
                ratio = ds_map_find_value(_score, "ratio");
            }
            if (ratio > 0.6) {
                msg = "¡Perfecto! That’s pure español, baby.";
            } else if (ratio > 0.4) {
                msg = "Nice balance — keep the mix alive.";
            } else {
                msg = "Good job — we’re getting warmer.";
            }
        }
    }
    return msg;
}
