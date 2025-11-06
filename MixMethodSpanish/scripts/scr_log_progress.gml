/// @function scr_log_progress(_seeder, _score)
/// @description Append progress information to a CSV file when a stage is cleared.
/// @param {ds_map} _seeder
/// @param {ds_map} _score
function scr_log_progress(_seeder, _score) {
    var path = "progress.csv";
    var exists = file_exists(path);
    var file = exists ? file_text_open_append(path) : file_text_open_write(path);

    if (!exists) {
        file_text_write_string(file, "timestamp,stage_id,cefr,used_tokens,ratio,register,pass,xp_total,mix_ratio");
        file_text_writeln(file);
    }

    var ts = date_datetime_string(date_current_datetime());
    var id = is_ds_map(_seeder) && ds_map_exists(_seeder, "id") ? ds_map_find_value(_seeder, "id") : "";
    var cefr = is_ds_map(_seeder) && ds_map_exists(_seeder, "cefr") ? ds_map_find_value(_seeder, "cefr") : "";
    var used = is_ds_map(_score) && ds_map_exists(_score, "used") ? ds_map_find_value(_score, "used") : 0;
    var ratio_val = is_ds_map(_score) && ds_map_exists(_score, "ratio") ? ds_map_find_value(_score, "ratio") : 0;
    var reg = scr_detect_register(keyboard_string);
    var pass_flag = is_ds_map(_score) && ds_map_exists(_score, "pass") ? ds_map_find_value(_score, "pass") : 0;
    var xp = string(global.profile.xp);
    var mix_ratio = string_format(global.profile.mix_ratio, 0, 2);

    var line = ts;
    line += "," + string(id);
    line += "," + string(cefr);
    line += "," + string(used);
    line += "," + string_format(ratio_val, 0, 2);
    line += "," + reg;
    line += "," + string(pass_flag);
    line += "," + xp;
    line += "," + mix_ratio;

    file_text_write_string(file, line);
    file_text_writeln(file);
    file_text_close(file);
}
