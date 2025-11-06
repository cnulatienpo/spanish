/// @function scr_score_ladder(_user, _seeder)
/// @description Evaluate ladder requirements including register and ratio logic.
/// @param {string} _user
/// @param {ds_map} _seeder
function scr_score_ladder(_user, _seeder) {
    var cefr = "A0";
    if (is_ds_map(_seeder) && ds_map_exists(_seeder, "cefr")) {
        cefr = ds_map_find_value(_seeder, "cefr");
    }
    var mix = undefined;
    if (is_ds_map(_seeder) && ds_map_exists(_seeder, "mix")) {
        mix = ds_map_find_value(_seeder, "mix");
    }
    var min = scr_mix_cefr_default_min(cefr);
    if (is_ds_map(mix) && ds_map_exists(mix, "min_tokens")) {
        min = ds_map_find_value(mix, "min_tokens");
    }

    var used = scr_count_spanish_tokens(_user, []);
    var toks = scr_tokenize(_user);
    var total = array_length(toks);
    var ratio = scr_spanish_ratio(_user);
    var pass = false;

    if (cefr == "C1") {
        pass = (ratio >= 0.4);
    } else if (cefr == "C2") {
        pass = (ratio >= 0.6);
    } else {
        pass = (used >= min);
    }

    var need = max(0, min - used);
    var reg_bonus = scr_register_score(_user, _seeder);

    var out = ds_map_create();
    ds_map_set(out, "pass", pass);
    ds_map_set(out, "used", used);
    ds_map_set(out, "need", need);
    ds_map_set(out, "ratio", ratio);
    ds_map_set(out, "total", total);
    ds_map_set(out, "register_bonus", reg_bonus);
    ds_map_set(out, "cefr", cefr);
    ds_map_set(out, "min_tokens", min);
    return out;
}
