/// @function scr_expected_register(_seeder)
/// @description Resolve the expected register for the given seeder.
/// @param {ds_map} _seeder
function scr_expected_register(_seeder) {
    if (!is_ds_map(_seeder)) {
        return "neutral";
    }
    if (!ds_map_exists(_seeder, "register")) {
        return "neutral";
    }
    var reg = ds_map_find_value(_seeder, "register");
    if (is_ds_map(reg) && ds_map_exists(reg, "expected")) {
        var v = string_lower(string(ds_map_find_value(reg, "expected")));
        if (v == "tu") {
            v = "tú";
        }
        return v;
    }
    return "neutral";
}
