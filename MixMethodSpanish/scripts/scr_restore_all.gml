/// @function scr_restore_all(_backup_dir)
/// @description Restore every JSON file inside a backup directory into the live seeders directory.
/// @param {string} _backup_dir
/// @returns {real} number of files successfully restored
function scr_restore_all(_backup_dir) {
    if (!is_string(_backup_dir) || _backup_dir == "" || !directory_exists(_backup_dir)) {
        return 0;
    }

    var files = scr_list_backup_files(_backup_dir);
    var restored = 0;

    for (var i = 0; i < array_length(files); i++) {
        if (scr_restore_file(files[i])) {
            restored += 1;
        }
    }

    return restored;
}
