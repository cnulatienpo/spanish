/// @function scr_live_path_for_backup_file(_backup_file)
/// @description Convert a backup file path to its live seeder path.
/// @param {string} _backup_file
/// @returns {string}
function scr_live_path_for_backup_file(_backup_file) {
    if (!is_string(_backup_file) || _backup_file == "") {
        return "";
    }

    var backup_dir = filename_path(_backup_file);
    var name = filename_name(_backup_file);
    var parent_dir = filename_path(backup_dir);

    if (parent_dir == "") {
        return "";
    }

    return parent_dir + "/" + name + ".json";
}
