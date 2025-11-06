/// @function scr_delete_backup_dir(_backup_dir)
/// @description Delete every file inside a backup directory and remove the directory itself.
/// @param {string} _backup_dir
/// @returns {boolean} success flag
function scr_delete_backup_dir(_backup_dir) {
    if (!is_string(_backup_dir) || _backup_dir == "" || !directory_exists(_backup_dir)) {
        return false;
    }

    var entry = file_find_first(_backup_dir + "/*", fa_readonly);
    while (entry != "") {
        var target = _backup_dir + "/" + string(entry);
        if (file_exists(target)) {
            file_delete(target);
        }
        entry = file_find_next();
    }
    file_find_close();

    return directory_delete(_backup_dir);
}
