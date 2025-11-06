/// @function scr_load_seeders()
/// @description Load seeder definitions from data/seeders/*.json into ds_maps.
function scr_load_seeders() {
    var list = [];
    var dir = "data/seeders/";
    var filename = file_find_first(dir + "*.json", fa_readonly);
    while (filename != "") {
        var path = dir + filename;
        var file = file_text_open_read(path);
        if (file != -1) {
            var json = "";
            while (!file_text_eof(file)) {
                json += file_text_read_string(file);
                if (!file_text_eof(file)) {
                    json += "\n";
                }
            }
            file_text_close(file);
            if (json != "") {
                var parsed = json_parse(json);
                if (is_struct(parsed)) {
                    parsed = scr_struct_to_ds_map(parsed);
                }
                if (is_ds_map(parsed)) {
                    array_push(list, parsed);
                }
            }
        }
        filename = file_find_next();
    }
    file_find_close();
    return list;
}
