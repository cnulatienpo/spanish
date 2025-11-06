/// @function scr_validate_seeder(_m)
/// @description Validate a seeder map and return human-readable errors.
/// @param {ds_map} _m
/// @returns {ds_list<string>} errors
function scr_validate_seeder(_m) {
    var errs = ds_list_create();
    if (!is_ds_map(_m)) {
        ds_list_add(errs, "Not an object");
        return errs;
    }

    if (!ds_map_exists(_m, "id") || string(ds_map_find_value(_m, "id")) == "") {
        ds_list_add(errs, "Missing 'id'");
    }
    if (!ds_map_exists(_m, "title") || string(ds_map_find_value(_m, "title")) == "") {
        ds_list_add(errs, "Missing 'title'");
    }
    if (!ds_map_exists(_m, "cefr") || !scr_seeder_cefr_ok(ds_map_find_value(_m, "cefr"))) {
        ds_list_add(errs, "Invalid or missing 'cefr' (A0..C2 required)");
    }
    if (!ds_map_exists(_m, "dialogue") || !is_array(ds_map_find_value(_m, "dialogue")) || array_length(ds_map_find_value(_m, "dialogue")) == 0) {
        ds_list_add(errs, "Missing or empty 'dialogue' array");
    }

    if (ds_map_exists(_m, "dialogue") && is_array(ds_map_find_value(_m, "dialogue"))) {
        var dlg = ds_map_find_value(_m, "dialogue");
        for (var i = 0; i < array_length(dlg); i++) {
            var turn = dlg[i];
            if (!is_ds_map(turn)) {
                ds_list_add(errs, "Dialogue[" + string(i) + "] is not an object");
                continue;
            }
            if (!(ds_map_exists(turn, "npc") || ds_map_exists(turn, "you") || ds_map_exists(turn, "es"))) {
                ds_list_add(errs, "Dialogue[" + string(i) + "] needs at least one of npc/you/es");
            }
        }
    }

    if (ds_map_exists(_m, "mix")) {
        var mix = ds_map_find_value(_m, "mix");
        if (!is_ds_map(mix)) {
            ds_list_add(errs, "'mix' must be an object");
        } else if (ds_map_exists(mix, "min_tokens")) {
            var min = ds_map_find_value(mix, "min_tokens");
            if (!(is_real(min) && min >= 0)) {
                ds_list_add(errs, "'mix.min_tokens' must be a non-negative number");
            }
        }
    }

    if (ds_map_exists(_m, "register")) {
        var reg = ds_map_find_value(_m, "register");
        if (!is_ds_map(reg)) {
            ds_list_add(errs, "'register' must be an object");
        } else {
            if (ds_map_exists(reg, "expected")) {
                var exp = string_lower(string(ds_map_find_value(reg, "expected")));
                if (!(exp == "tú" || exp == "tu" || exp == "usted" || exp == "slang" || exp == "neutral")) {
                    ds_list_add(errs, "'register.expected' must be 'tú'|'usted'|'slang'|'neutral'");
                }
            }
            if (ds_map_exists(reg, "bonus")) {
                var bonus = ds_map_find_value(reg, "bonus");
                if (!(is_real(bonus) && bonus >= 0)) {
                    ds_list_add(errs, "'register.bonus' must be >= 0");
                }
            }
            if (ds_map_exists(reg, "examples")) {
                var ex = ds_map_find_value(reg, "examples");
                if (!is_array(ex)) {
                    ds_list_add(errs, "'register.examples' must be array<string>");
                }
            }
        }
    }

    if (ds_map_exists(_m, "targets")) {
        var trg = ds_map_find_value(_m, "targets");
        if (!is_ds_map(trg)) {
            ds_list_add(errs, "'targets' must be an object");
        } else if (ds_map_exists(trg, "expected_spanish")) {
            var arr = ds_map_find_value(trg, "expected_spanish");
            if (!is_array(arr)) {
                ds_list_add(errs, "'targets.expected_spanish' must be array<string>");
            }
        }
    }

    if (ds_map_exists(_m, "rewards")) {
        var rw = ds_map_find_value(_m, "rewards");
        if (!is_ds_map(rw)) {
            ds_list_add(errs, "'rewards' must be an object");
        } else {
            if (ds_map_exists(rw, "xp") && !(is_real(ds_map_find_value(rw, "xp")))) {
                ds_list_add(errs, "'rewards.xp' must be a number");
            }
            if (ds_map_exists(rw, "mix_bump")) {
                var bump = ds_map_find_value(rw, "mix_bump");
                if (!(is_real(bump) && bump >= 0)) {
                    ds_list_add(errs, "'rewards.mix_bump' must be >= 0");
                }
            }
        }
    }

    return errs;
}
