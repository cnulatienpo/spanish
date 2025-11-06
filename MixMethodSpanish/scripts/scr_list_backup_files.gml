/// @function scr_list_backup_files(_dir)
/// @description Enumerate JSON files contained in a backup directory.
/// @param {string} _dir
/// @returns {array<string>} absolute paths to JSON files in the directory.
function scr_list_backup_files(_dir) {
    var files = [];

    if (!is_string(_dir) || _dir == "" || !directory_exists(_dir)) {
        return files;
    }

    var search = file_find_first(_dir + "/*.json", fa_readonly);
    while (search != "") {
        array_push(files, _dir + "/" + string(search));
        search = file_find_next();
    }
    file_find_close();

    array_sort(files, function(_a, _b) {
        return string_compare(_a, _b);
    });

    return files;
}
