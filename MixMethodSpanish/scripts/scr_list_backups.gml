/// @function scr_list_backups()
/// @description Collect backup directories under data/seeders sorted newest first.
/// @returns {array<string>} absolute paths to backup directories.
function scr_list_backups() {
    var root = "data/seeders";
    var results = [];

    if (!directory_exists(root)) {
        return results;
    }

    var search = file_find_first(root + "/*", fa_directory);
    while (search != "") {
        var folder = string(search);
        if (string_pos("_backup_", folder) > 0) {
            array_push(results, root + "/" + folder);
        }
        search = file_find_next();
    }
    file_find_close();

    array_sort(results, function(_a, _b) {
        return -string_compare(_a, _b);
    });

    return results;
}
