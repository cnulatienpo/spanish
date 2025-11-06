/// @function scr_set_last_selected_id(_id)
/// @description Persist the last selected seeder id into globals/profile.
/// @param {string} _id
/// @returns {string} Stored id value.
function scr_set_last_selected_id(_id) {
    var id_str = "";
    if (!is_undefined(_id)) {
        id_str = string(_id);
        if (id_str == "-1") {
            id_str = "";
        }
    }
    global.last_selected_id = id_str;
    if (is_struct(global.profile)) {
        global.profile.last_selected_id = id_str;
    }
    return id_str;
}
