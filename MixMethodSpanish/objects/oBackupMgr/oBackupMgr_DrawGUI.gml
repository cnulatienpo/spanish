/// @description Draw the backup manager modal overlay.
function oBackupMgr_DrawGUI() {
    if (!active) {
        return;
    }

    var gui_w = display_get_gui_width();
    var gui_h = display_get_gui_height();
    var mx = device_mouse_x_to_gui(0);
    var my = device_mouse_y_to_gui(0);
    var clicked = mouse_check_button_pressed(mb_left);
    var wheel_up = mouse_wheel_up();
    var wheel_down = mouse_wheel_down();

    draw_set_font(f_ui);
    draw_set_halign(fa_left);
    draw_set_valign(fa_top);

    draw_set_alpha(0.88);
    draw_set_color(make_color_rgb(20, 20, 25));
    draw_rectangle(0, 0, gui_w, gui_h, false);
    draw_set_alpha(1);

    var pad = 16;
    var panel_w = gui_w - pad * 2;
    var panel_h = gui_h - pad * 2;
    var px = pad;
    var py = pad;

    draw_set_color(make_color_rgb(50, 50, 60));
    draw_rectangle(px, py, px + panel_w, py + panel_h, false);

    draw_set_color(c_white);
    draw_text(px + 12, py + 10, "📦 Backup Manager (press ESC to close)");

    var col1 = 260;
    var col2 = 360;
    var col3 = max(0, panel_w - col1 - col2 - 40);
    var y0 = py + 40;

    // Backups list panel
    var backups_x = px + 12;
    var backups_y = y0;
    var backups_w = col1;
    var backups_h = panel_h - 120;
    if (backups_h < 0) backups_h = 0;

    draw_set_color(make_color_rgb(30, 30, 35));
    draw_rectangle(backups_x, backups_y, backups_x + backups_w, backups_y + backups_h, false);

    var row_h = 26;
    var backups_total_h = array_length(backups) * (row_h + 4);
    var backups_max_scroll = max(0, backups_total_h - backups_h + 4);
    var y = backups_y - left_scroll;
    for (var i = 0; i < array_length(backups); i++) {
        var dir_path = backups[i];
        var label = filename_name(dir_path);
        var hover = point_in_rectangle(mx, my, backups_x, y, backups_x + backups_w, y + row_h);
        var bg_col;
        if (dir_path == selected_backup) {
            bg_col = make_color_hsv(210, 15, 45);
        } else if (hover) {
            bg_col = make_color_hsv(210, 10, 35);
        } else {
            bg_col = make_color_hsv(210, 10, 25);
        }
        draw_set_color(bg_col);
        draw_rectangle(backups_x, y, backups_x + backups_w, y + row_h, false);
        draw_set_color(c_white);
        draw_text(backups_x + 8, y + 6, label);

        if (clicked && hover) {
            selected_backup = dir_path;
            files = scr_list_backup_files(selected_backup);
            selected_file = (array_length(files) > 0) ? files[0] : "";
        }

        y += row_h + 4;
    }

    if (point_in_rectangle(mx, my, backups_x, backups_y, backups_x + backups_w, backups_y + backups_h)) {
        var delta = (wheel_down - wheel_up) * 40;
        if (delta != 0) {
            left_scroll = clamp(left_scroll + delta, 0, backups_max_scroll);
        }
    }
    left_scroll = clamp(left_scroll, 0, backups_max_scroll);

    // Files list panel
    var files_x = backups_x + backups_w + 12;
    var files_y = y0;
    var files_w = col2;
    var files_h = panel_h - 120;
    if (files_h < 0) files_h = 0;

    draw_set_color(make_color_rgb(30, 30, 35));
    draw_rectangle(files_x, files_y, files_x + files_w, files_y + files_h, false);

    var row_h2 = 24;
    var files_total_h = array_length(files) * (row_h2 + 3);
    var files_max_scroll = max(0, files_total_h - files_h + 3);
    y = files_y - right_scroll;
    for (var j = 0; j < array_length(files); j++) {
        var file_path = files[j];
        var file_name = filename_name(file_path) + ".json";
        var hover_file = point_in_rectangle(mx, my, files_x, y, files_x + files_w, y + row_h2);
        var file_col;
        if (file_path == selected_file) {
            file_col = make_color_hsv(140, 15, 45);
        } else if (hover_file) {
            file_col = make_color_hsv(140, 10, 35);
        } else {
            file_col = make_color_hsv(140, 10, 25);
        }
        draw_set_color(file_col);
        draw_rectangle(files_x, y, files_x + files_w, y + row_h2, false);
        draw_set_color(c_white);
        draw_text(files_x + 8, y + 5, file_name);

        if (clicked && hover_file) {
            selected_file = file_path;
        }

        y += row_h2 + 3;
    }

    if (point_in_rectangle(mx, my, files_x, files_y, files_x + files_w, files_y + files_h)) {
        var delta_files = (wheel_down - wheel_up) * 40;
        if (delta_files != 0) {
            right_scroll = clamp(right_scroll + delta_files, 0, files_max_scroll);
        }
    }
    right_scroll = clamp(right_scroll, 0, files_max_scroll);

    // Preview and diff panel
    var preview_x = files_x + files_w + 12;
    var preview_y = y0;
    var preview_w = col3;
    var preview_h = panel_h - 120;
    if (preview_h < 0) preview_h = 0;

    draw_set_color(make_color_rgb(30, 30, 35));
    draw_rectangle(preview_x, preview_y, preview_x + preview_w, preview_y + preview_h, false);

    if (selected_file != "" && preview_w > 0) {
        var live_path = scr_live_path_for_backup_file(selected_file);
        var backup_txt = scr_read_text(selected_file);
        var live_txt = scr_read_text(live_path);

        draw_set_color(c_white);
        draw_text(preview_x + 8, preview_y + 6, "Preview + Diff");
        draw_text(preview_x + 8, preview_y + 26, "Backup: " + filename_name(selected_file) + ".json");
        draw_text(preview_x + preview_w * 0.5, preview_y + 26, "Live: " + filename_name(live_path) + ".json");

        var line_height = 14;
        var text_y = preview_y + 46;
        var right_col_x = preview_x + (preview_w * 0.5) + 6;

        draw_set_color(make_color_rgb(200, 200, 220));
        var lines_backup = string_split(backup_txt, "\n");
        var max_lines_backup = min(22, array_length(lines_backup));
        for (var bi = 0; bi < max_lines_backup; bi++) {
            draw_text(preview_x + 8, text_y + bi * line_height, string_copy(lines_backup[bi], 1, 120));
        }

        draw_set_color(make_color_rgb(220, 200, 200));
        var lines_live = string_split(live_txt, "\n");
        var max_lines_live = min(22, array_length(lines_live));
        for (var li = 0; li < max_lines_live; li++) {
            draw_text(right_col_x, text_y + li * line_height, string_copy(lines_live[li], 1, 120));
        }

        var diff_y = text_y + 24 * line_height;
        var diff_raw = scr_diff_lines(backup_txt, live_txt);
        var diff_show = min(12, ds_list_size(diff_raw));
        var diff_entries = [];
        for (var di = 0; di < diff_show; di++) {
            var entry = ds_list_find_value(diff_raw, di);
            if (is_ds_map(entry)) {
                var entry_type = ds_map_find_value(entry, "type");
                var entry_text = ds_map_find_value(entry, "text");
                array_push(diff_entries, [entry_type, entry_text]);
            }
        }
        for (var di_all = 0; di_all < ds_list_size(diff_raw); di_all++) {
            var entry_all = ds_list_find_value(diff_raw, di_all);
            if (is_ds_map(entry_all)) {
                ds_map_destroy(entry_all);
            }
        }
        ds_list_destroy(diff_raw);

        for (var dk = 0; dk < array_length(diff_entries); dk++) {
            var type_text = diff_entries[dk];
            var diff_type = type_text[0];
            var diff_text = string_copy(type_text[1], 1, 120);
            if (diff_type == "+") {
                draw_set_color(c_lime);
            } else if (diff_type == "-") {
                draw_set_color(c_red);
            } else {
                draw_set_color(c_white);
            }
            draw_text(preview_x + 8, diff_y + dk * line_height, diff_type + " " + diff_text);
        }
    }

    // Bottom buttons
    var buttons_y = py + panel_h - 64;
    var button_w = 160;
    var button_h = 28;

    var restore_file_x = preview_x;
    var restore_file_hover = point_in_rectangle(mx, my, restore_file_x, buttons_y, restore_file_x + button_w, buttons_y + button_h);
    draw_set_color(restore_file_hover ? c_lime : c_dkgray);
    draw_rectangle(restore_file_x, buttons_y, restore_file_x + button_w, buttons_y + button_h, false);
    draw_set_halign(fa_center);
    draw_set_valign(fa_middle);
    draw_set_color(c_white);
    draw_text(restore_file_x + button_w * 0.5, buttons_y + button_h * 0.5, "Restore File");

    if (clicked && restore_file_hover && selected_file != "") {
        if (scr_restore_file(selected_file)) {
            global.seeders = scr_load_seeders();
            global.seeder_errors = scr_validate_all_seeders(global.seeders);
            if (object_exists(oSelect)) {
                with (oSelect) { oSelect_Create(); }
            }
            toast_text = "Restored: " + filename_name(selected_file) + ".json";
            toast_timer = current_time;
        } else {
            toast_text = "Restore failed (permissions?)";
            toast_timer = current_time;
        }
    }

    var restore_all_x = restore_file_x + button_w + 12;
    var restore_all_hover = point_in_rectangle(mx, my, restore_all_x, buttons_y, restore_all_x + button_w, buttons_y + button_h);
    draw_set_color(restore_all_hover ? make_color_hsv(140, 60, 80) : c_dkgray);
    draw_rectangle(restore_all_x, buttons_y, restore_all_x + button_w, buttons_y + button_h, false);
    draw_set_color(c_white);
    draw_text(restore_all_x + button_w * 0.5, buttons_y + button_h * 0.5, "Restore All");

    if (clicked && restore_all_hover && selected_backup != "") {
        var restored_count = scr_restore_all(selected_backup);
        global.seeders = scr_load_seeders();
        global.seeder_errors = scr_validate_all_seeders(global.seeders);
        if (object_exists(oSelect)) {
            with (oSelect) { oSelect_Create(); }
        }
        toast_text = "Restored " + string(restored_count) + " file(s) from " + filename_name(selected_backup);
        toast_timer = current_time;
    }

    var delete_x = restore_all_x + button_w + 12;
    var delete_hover = point_in_rectangle(mx, my, delete_x, buttons_y, delete_x + button_w, buttons_y + button_h);
    draw_set_color(delete_hover ? make_color_hsv(0, 60, 80) : c_dkgray);
    draw_rectangle(delete_x, buttons_y, delete_x + button_w, buttons_y + button_h, false);
    draw_set_color(c_white);
    draw_text(delete_x + button_w * 0.5, buttons_y + button_h * 0.5, "Delete Backup");

    if (clicked && delete_hover && selected_backup != "") {
        if (scr_delete_backup_dir(selected_backup)) {
            backups = scr_list_backups();
            selected_backup = (array_length(backups) > 0) ? backups[0] : "";
            files = (selected_backup != "") ? scr_list_backup_files(selected_backup) : [];
            selected_file = (array_length(files) > 0) ? files[0] : "";
            toast_text = "Backup deleted.";
            toast_timer = current_time;
        } else {
            toast_text = "Delete failed.";
            toast_timer = current_time;
        }
    }

    draw_set_halign(fa_left);
    draw_set_valign(fa_top);

    if (toast_text != "") {
        if (current_time - toast_timer < 3000) {
            draw_set_color(c_white);
            draw_set_halign(fa_center);
            draw_set_valign(fa_middle);
            draw_text(gui_w * 0.5, gui_h - 32, toast_text);
            draw_set_halign(fa_left);
            draw_set_valign(fa_top);
        } else {
            toast_text = "";
        }
    }
}
