/// @function scr_register_label(_seeder)
/// @description Register label for a seeder.
/// @param {ds_map} _seeder
function scr_register_label(_seeder) {
    if (!is_ds_map(_seeder)) {
        return "Register: —";
    }
    if (!ds_map_exists(_seeder, "register")) {
        return "Register: —";
    }
    var reg = ds_map_find_value(_seeder, "register");
    if (!is_ds_map(reg)) {
        return "Register: —";
    }
    var exp = "";
    if (ds_map_exists(reg, "expected")) {
        exp = ds_map_find_value(reg, "expected");
    }
    if (is_undefined(exp) || exp == "") {
        return "Register: —";
    }
    return "Register: " + string(exp);
}
