/// @function scr_restore_file(_backup_file)
/// @description Copy a single backup JSON file into the live seeders directory.
/// @param {string} _backup_file
/// @returns {boolean} success flag
function scr_restore_file(_backup_file) {
    if (!is_string(_backup_file) || _backup_file == "") {
        return false;
    }

    var live_path = scr_live_path_for_backup_file(_backup_file);
    if (live_path == "") {
        return false;
    }

    var contents = scr_read_text(_backup_file);
    if (contents == "") {
        return false;
    }

    var fh = file_text_open_write(live_path);
    if (fh == -1) {
        return false;
    }
    file_text_write_string(fh, contents);
    file_text_close(fh);

    return true;
}
