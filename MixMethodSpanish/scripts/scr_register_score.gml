/// @function scr_register_score(_user, _seeder)
/// @description Determine the register bonus when the expected register is matched.
/// @param {string} _user
/// @param {ds_map} _seeder
function scr_register_score(_user, _seeder) {
    if (!is_ds_map(_seeder)) {
        return 0;
    }
    if (!ds_map_exists(_seeder, "register")) {
        return 0;
    }
    var reg = ds_map_find_value(_seeder, "register");
    if (!is_ds_map(reg)) {
        return 0;
    }
    if (!ds_map_exists(reg, "expected")) {
        return 0;
    }
    var expected = ds_map_find_value(reg, "expected");
    var bonus = 0;
    if (ds_map_exists(reg, "bonus")) {
        bonus = ds_map_find_value(reg, "bonus");
    }
    if (scr_detect_register(_user) == expected) {
        return bonus;
    }
    return 0;
}
