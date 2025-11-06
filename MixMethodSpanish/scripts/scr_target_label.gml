/// @function scr_target_label(_seeder)
/// @description Human-readable target label (min tokens or ratio) for a seeder.
/// @param {ds_map} _seeder
function scr_target_label(_seeder) {
    if (!is_ds_map(_seeder)) {
        return "Target: —";
    }
    var cefr = "";
    if (ds_map_exists(_seeder, "cefr")) {
        cefr = ds_map_find_value(_seeder, "cefr");
    }
    if (cefr == "C1") {
        return "Target: ≥40% Spanish";
    }
    if (cefr == "C2") {
        return "Target: ≥60% Spanish";
    }
    var mix = -1;
    if (ds_map_exists(_seeder, "mix")) {
        mix = ds_map_find_value(_seeder, "mix");
    }
    var min = (is_ds_map(mix) && ds_map_exists(mix, "min_tokens"))
        ? ds_map_find_value(mix, "min_tokens")
        : scr_mix_cefr_default_min(cefr);
    return "Target: ≥" + string(min) + " Spanish word(s)";
}
