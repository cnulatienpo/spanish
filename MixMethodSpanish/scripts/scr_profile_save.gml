/// @function scr_profile_save(_profile)
/// @description Persist the profile struct as JSON under data/profile.json.
function scr_profile_save(_profile) {
    var path = "data/profile.json";
    var json = json_stringify(_profile);
    var file = file_text_open_write(path);
    if (file == -1) {
        return false;
    }
    file_text_write_string(file, json);
    file_text_close(file);
    return true;
}
