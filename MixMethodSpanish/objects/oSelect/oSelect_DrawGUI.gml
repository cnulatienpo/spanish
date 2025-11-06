/// @description Render the stage select UI with theming and settings access.
function oSelect_DrawGUI() {
    if (!is_struct(global.settings)) {
        scr_settings_defaults();
    }
    var settings = global.settings;
    var font_scale = settings.font_scale;
    var high_contrast = settings.theme_high_contrast;
    var text_col = high_contrast ? c_white : c_white;
    var subhead_col = high_contrast ? c_white : c_silver;
    var background_col = high_contrast ? c_black : make_color_rgb(24, 24, 32);
    var card_color = high_contrast ? make_color_rgb(60, 60, 60) : make_color_hsv(210, 10, 25);
    var card_hover = high_contrast ? make_color_rgb(110, 110, 110) : make_color_hsv(210, 15, 35);
    var search_bg = high_contrast ? make_color_rgb(10, 10, 10) : make_color_rgb(40, 40, 50);
    var search_outline = high_contrast ? c_white : c_white;
    var button_base = high_contrast ? make_color_rgb(220, 220, 220) : c_dkgray;
    var button_hover_col = high_contrast ? make_color_rgb(255, 255, 255) : make_color_hsv(210, 20, 60);
    var button_text_col = high_contrast ? c_black : c_white;
    var play_button_hover = high_contrast ? make_color_rgb(30, 200, 30) : c_lime;
    var preview_button_hover = high_contrast ? make_color_rgb(200, 150, 0) : make_color_hsv(40, 60, 80);
    var preview_bg = high_contrast ? c_white : make_color_hsv(210, 10, 18);
    var preview_text = high_contrast ? c_black : c_white;

    var W = display_get_gui_width();
    var H = display_get_gui_height();

    draw_set_font(f_ui);
    draw_set_halign(fa_left);
    draw_set_valign(fa_top);

    draw_set_color(background_col);
    draw_rectangle(0, 0, W, H, false);

    draw_set_color(text_col);

    var draw_text_scaled = function(_x, _y, _text) {
        draw_text_transformed(_x, _y, _text, font_scale, font_scale, 0);
    };

    draw_text_scaled(ui_pad, ui_pad, "Mix Method Spanish — Stage Select");
    draw_text_scaled(ui_pad, ui_pad + 24, "Search:");

    var search_x1 = ui_pad + 64;
    var search_y1 = ui_pad + 18;
    var search_x2 = search_x1 + 360;
    var search_y2 = search_y1 + 24;
    draw_set_color(search_bg);
    draw_rectangle(search_x1, search_y1, search_x2, search_y2, false);
    draw_set_color(search_outline);
    draw_rectangle(search_x1, search_y1, search_x2, search_y2, true);
    draw_set_color(text_col);
    draw_text_transformed(search_x1 + 8, search_y1 + 4, search_q, font_scale, font_scale, 0);

    var list_x = ui_pad;

    var settings_active = scr_settings_is_active();
    var mx = device_mouse_x_to_gui(0);
    var my = device_mouse_y_to_gui(0);
    var mouse_clicked = mouse_check_button_pressed(mb_left);
    var clicked = !settings_active && mouse_clicked;

    if (object_exists(oBackupMgr)) {
        var backup_btn_x = list_x + 660;
        var backup_btn_y = ui_pad;
        var backup_btn_w = 120;
        var backup_btn_h = 26;
        var backup_hover = point_in_rectangle(mx, my, backup_btn_x, backup_btn_y, backup_btn_x + backup_btn_w, backup_btn_y + backup_btn_h);
        draw_set_color(backup_hover ? button_hover_col : button_base);
        draw_rectangle(backup_btn_x, backup_btn_y, backup_btn_x + backup_btn_w, backup_btn_y + backup_btn_h, false);
        draw_set_halign(fa_center);
        draw_set_valign(fa_middle);
        draw_set_color(button_text_col);
        draw_text_transformed(backup_btn_x + backup_btn_w * 0.5, backup_btn_y + backup_btn_h * 0.5, "Backups", font_scale, font_scale, 0);
        draw_set_halign(fa_left);
        draw_set_valign(fa_top);

        if (mouse_clicked && !settings_active && backup_hover) {
            with (oBackupMgr) {
                backups = scr_list_backups();
                selected_backup = (array_length(backups) > 0) ? backups[0] : "";
                files = (selected_backup != "") ? scr_list_backup_files(selected_backup) : [];
                selected_file = (array_length(files) > 0) ? files[0] : "";
                left_scroll = 0;
                right_scroll = 0;
                toast_text = "";
                active = true;
            }
        }
    }

    var cbx = list_x + 380;
    var cby = ui_pad + 20;
    var cbw = 14;
    var cbh = 14;
    var cb_hover = point_in_rectangle(mx, my, cbx, cby, cbx + cbw, cby + cbh);
    draw_set_color(c_dkgray);
    draw_rectangle(cbx, cby, cbx + cbw, cby + cbh, false);
    if (hide_invalid) {
        draw_set_color(c_lime);
        draw_rectangle(cbx + 3, cby + 3, cbx + cbw - 3, cby + cbh - 3, false);
    }
    draw_set_color(text_col);
    draw_text_transformed(cbx + cbw + 8, cby - 2, "Hide invalid", font_scale, font_scale, 0);
    if (mouse_clicked && !settings_active && cb_hover) {
        hide_invalid = !hide_invalid;
    }

    var gear_size = 24;
    var gear_x = W - gear_size - 16;
    var gear_y = ui_pad;
    var gear_hover = point_in_rectangle(mx, my, gear_x, gear_y, gear_x + gear_size, gear_y + gear_size);
    draw_set_color(gear_hover ? button_hover_col : button_base);
    draw_rectangle(gear_x, gear_y, gear_x + gear_size, gear_y + gear_size, false);
    draw_set_color(c_black);
    draw_rectangle(gear_x, gear_y, gear_x + gear_size, gear_y + gear_size, true);
    draw_set_color(button_text_col);
    draw_set_halign(fa_center);
    draw_set_valign(fa_middle);
    draw_text_transformed(gear_x + gear_size * 0.5, gear_y + gear_size * 0.5, "⚙", font_scale, font_scale, 0);
    draw_set_halign(fa_left);
    draw_set_valign(fa_top);
    draw_set_color(text_col);

    if (mouse_clicked && gear_hover && object_exists(oSettings)) {
        with (oSettings) active = !active;
    }

    if (!is_ds_map(global.seeder_errors)) {
        global.seeder_errors = scr_validate_all_seeders(global.seeders);
    }
    var errors_map = global.seeder_errors;

    var seeder_error_list = function(_map) {
        if (!is_ds_map(_map)) {
            return -1;
        }
        var key = "";
        if (ds_map_exists(_map, "__validator_key")) {
            key = ds_map_find_value(_map, "__validator_key");
        } else if (ds_map_exists(_map, "id")) {
            key = string(ds_map_find_value(_map, "id"));
        }
        if (is_ds_map(errors_map) && ds_map_exists(errors_map, key)) {
            return ds_map_find_value(errors_map, key);
        }
        return -1;
    };

    var seeder_visible = function(_entry) {
        if (!is_ds_map(_entry) || ds_map_exists(_entry, "__section")) {
            return false;
        }
        var arr = scr_filter_seeders([_entry], search_q);
        if (array_length(arr) == 0) {
            return false;
        }
        if (hide_invalid && scr_has_errors(seeder_error_list(_entry))) {
            return false;
        }
        return true;
    };

    var filtered = [];
    if (is_array(sorted)) {
        for (var i = 0; i < array_length(sorted); i++) {
            var entry = sorted[i];
            if (is_ds_map(entry) && ds_map_exists(entry, "__section")) {
                var band = ds_map_find_value(entry, "__section");
                var has_match = false;
                for (var k = i + 1; k < array_length(sorted); k++) {
                    var peek = sorted[k];
                    if (is_ds_map(peek) && ds_map_exists(peek, "__section")) {
                        break;
                    }
                    if (seeder_visible(peek)) {
                        has_match = true;
                        break;
                    }
                }
                if (has_match) {
                    array_push(filtered, entry);
                }
            } else {
                if (seeder_visible(entry)) {
                    array_push(filtered, entry);
                }
            }
        }
    }

    var content_height = 0;
    var last_was_card = false;
    for (var fi = 0; fi < array_length(filtered); fi++) {
        var fit = filtered[fi];
        if (is_ds_map(fit) && ds_map_exists(fit, "__section")) {
            content_height += 26;
            last_was_card = false;
        } else {
            content_height += card_h + gap_y;
            last_was_card = true;
        }
    }
    if (last_was_card && content_height >= gap_y) {
        content_height -= gap_y;
    }
    var visible_h = H - (ui_pad + 64) - ui_pad;
    if (visible_h < 0) visible_h = 0;
    scroll_max = max(0, content_height - visible_h);
    scroll_y = clamp(scroll_y, 0, scroll_max);

    var list_y = ui_pad + 64;
    var list_w = max(220, min(W - ui_pad * 2, col_w));
    var y = list_y - scroll_y;

    for (var i2 = 0; i2 < array_length(filtered); i2++) {
        var item = filtered[i2];
        if (is_ds_map(item) && ds_map_exists(item, "__section")) {
            var band = ds_map_find_value(item, "__section");
            draw_set_color(subhead_col);
            draw_text_transformed(list_x, y, "— " + string(band) + " —", font_scale, font_scale, 0);
            y += 26;
            continue;
        }

        var x1 = list_x;
        var x2 = list_x + list_w;
        var y1 = y;
        var y2 = y + card_h;
        var hover = point_in_rectangle(mx, my, x1, y1, x2, y2);
        draw_set_color(hover ? card_hover : card_color);
        draw_rectangle(x1, y1, x2, y2, false);
        draw_set_color(c_black);
        draw_rectangle(x1, y1, x2, y2, true);

        var id = ds_map_exists(item, "id") ? ds_map_find_value(item, "id") : "";
        var title = ds_map_exists(item, "title") ? ds_map_find_value(item, "title") : "Untitled";
        var cefr = ds_map_exists(item, "cefr") ? ds_map_find_value(item, "cefr") : "?";
        var tgt = scr_target_label(item);
        var reg = scr_register_label(item);
        var validator_key = ds_map_exists(item, "__validator_key") ? ds_map_find_value(item, "__validator_key") : id;
        var errs = seeder_error_list(item);
        var has_errs = scr_has_errors(errs);
        var display_id = (string(id) != "") ? string(id) : string(validator_key);

        draw_set_color(text_col);
        draw_set_halign(fa_left);
        draw_set_valign(fa_top);
        draw_text_transformed(x1 + 10, y1 + 8, string(title) + "  (" + string(cefr) + ")", font_scale, font_scale, 0);
        draw_text_transformed(x1 + 10, y1 + 30, tgt, font_scale, font_scale, 0);
        draw_text_transformed(x1 + 10, y1 + 48, reg, font_scale, font_scale, 0);

        if (has_errs) {
            draw_set_color(make_color_rgb(255, 200, 60));
            draw_text_transformed(x1 + 10, y1 + card_h - 20, "⚠ " + string(ds_list_size(errs)) + " issue(s)", font_scale, font_scale, 0);
            draw_set_color(text_col);
        }

        var b_w = 88;
        var b_h = 28;
        var play_x1 = x2 - (b_w * 2 + 24);
        var prev_x1 = x2 - (b_w + 12);
        var by = y1 + card_h - b_h - 8;

        var play_hover = point_in_rectangle(mx, my, play_x1, by, play_x1 + b_w, by + b_h);
        var preview_hover = point_in_rectangle(mx, my, prev_x1, by, prev_x1 + b_w, by + b_h);

        draw_set_color(play_hover ? play_button_hover : button_base);
        draw_rectangle(play_x1, by, play_x1 + b_w, by + b_h, false);
        draw_set_color(c_black);
        draw_rectangle(play_x1, by, play_x1 + b_w, by + b_h, true);
        draw_set_color(button_text_col);
        draw_set_halign(fa_center);
        draw_set_valign(fa_middle);
        draw_text_transformed(play_x1 + b_w * 0.5, by + b_h * 0.5, "Play", font_scale, font_scale, 0);

        draw_set_color(preview_hover ? preview_button_hover : button_base);
        draw_rectangle(prev_x1, by, prev_x1 + b_w, by + b_h, false);
        draw_set_color(c_black);
        draw_rectangle(prev_x1, by, prev_x1 + b_w, by + b_h, true);
        draw_set_color(button_text_col);
        draw_text_transformed(prev_x1 + b_w * 0.5, by + b_h * 0.5, "Preview", font_scale, font_scale, 0);
        draw_set_halign(fa_left);
        draw_set_valign(fa_top);
        draw_set_color(text_col);

        if (hover && has_errs) {
            var tipw = 420;
            var tipx = min(mx + 14, display_get_gui_width() - tipw - 10);
            var tipy = my + 14;
            var total = is_ds_list(errs) ? ds_list_size(errs) : 0;
            var tiph = min(200, 24 * (total + 1));
            draw_set_color(make_color_rgb(30, 30, 30));
            draw_rectangle(tipx, tipy, tipx + tipw, tipy + tiph, false);
            draw_set_color(c_white);
            draw_text(tipx + 10, tipy + 6, "Seeder issues for: " + string(display_id));
            var yy = tipy + 28;
            if (is_ds_list(errs)) {
                var show_n = min(6, ds_list_size(errs));
                for (var ei = 0; ei < show_n; ei++) {
                    draw_text(tipx + 10, yy, "- " + ds_list_find_value(errs, ei));
                    yy += 20;
                }
                if (ds_list_size(errs) > show_n) {
                    draw_text(tipx + 10, yy, "…and more");
                }
            }
            draw_set_color(text_col);
        }

        if (clicked) {
            if (play_hover) {
                global.current_seeder = item;
                selected_id = string(id);
                scr_set_last_selected_id(id);
                scr_profile_save(global.profile);
                room_goto(r_typing);
                return;
            }
            if (preview_hover) {
                preview_map = item;
                selected_id = string(id);
                scr_set_last_selected_id(id);
                scr_profile_save(global.profile);
            } else if (hover) {
                selected_id = string(id);
            }
        }

        if (string(selected_id) == string(id)) {
            draw_set_color(high_contrast ? make_color_rgb(120, 200, 255) : c_aqua);
            draw_text_transformed(x1 + 10, y2 - 20, "Selected", font_scale, font_scale, 0);
            draw_set_color(text_col);
        }

        y += card_h + gap_y;
    }

    if (is_ds_map(preview_map)) {
        var w2 = min(560, W - 40);
        var h2 = min(360, H - 80);
        var px = (W - w2) / 2;
        var py = (H - h2) / 2;

        draw_set_color(preview_bg);
        draw_rectangle(px, py, px + w2, py + h2, false);
        draw_set_color(c_black);
        draw_rectangle(px, py, px + w2, py + h2, true);
        draw_set_color(preview_text);
        draw_set_halign(fa_left);
        draw_set_valign(fa_top);

        var p_id = ds_map_exists(preview_map, "id") ? ds_map_find_value(preview_map, "id") : "";
        var p_title = ds_map_exists(preview_map, "title") ? ds_map_find_value(preview_map, "title") : "";
        var p_cefr = ds_map_exists(preview_map, "cefr") ? ds_map_find_value(preview_map, "cefr") : "";
        draw_text_transformed(px + 16, py + 14, string(p_title) + " (" + string(p_cefr) + ")", font_scale, font_scale, 0);
        draw_text_transformed(px + 16, py + 36, scr_target_label(preview_map), font_scale, font_scale, 0);
        draw_text_transformed(px + 16, py + 56, scr_register_label(preview_map), font_scale, font_scale, 0);

        var dlg = ds_map_exists(preview_map, "dialogue") ? ds_map_find_value(preview_map, "dialogue") : -1;
        var y2 = py + 86;
        if (is_array(dlg)) {
            for (var di = 0; di < min(3, array_length(dlg)); di++) {
                var turn = dlg[di];
                if (!is_ds_map(turn)) {
                    continue;
                }
                var who = ds_map_exists(turn, "npc") ? ds_map_find_value(turn, "npc") : "";
                var you = ds_map_exists(turn, "you") ? ds_map_find_value(turn, "you") : "";
                var es = ds_map_exists(turn, "es") ? ds_map_find_value(turn, "es") : "";
                var speaker = "";
                var text = "";
                if (you != "") {
                    speaker = "You";
                    text = string(you);
                } else if (who != "") {
                    speaker = string(who);
                    text = string(es);
                } else {
                    text = string(es);
                }
                var line = (speaker != "") ? speaker + ": " + string(text) : string(text);
                draw_text_transformed(px + 16, y2, line, font_scale, font_scale, 0);
                y2 += 20 * font_scale;
            }
        }

        var bw = 110;
        var bh = 30;
        var bx1 = px + w2 - bw - 16;
        var by1 = py + h2 - bh - 16;
        var bx2 = bx1 - bw - 12;

        var play_hover2 = point_in_rectangle(mx, my, bx1, by1, bx1 + bw, by1 + bh);
        var close_hover = point_in_rectangle(mx, my, bx2, by1, bx2 + bw, by1 + bh);

        draw_set_halign(fa_center);
        draw_set_valign(fa_middle);

        draw_set_color(play_hover2 ? play_button_hover : button_base);
        draw_rectangle(bx1, by1, bx1 + bw, by1 + bh, false);
        draw_set_color(c_black);
        draw_rectangle(bx1, by1, bx1 + bw, by1 + bh, true);
        draw_set_color(button_text_col);
        draw_text_transformed(bx1 + bw * 0.5, by1 + bh * 0.5, "Play", font_scale, font_scale, 0);

        draw_set_color(close_hover ? preview_button_hover : button_base);
        draw_rectangle(bx2, by1, bx2 + bw, by1 + bh, false);
        draw_set_color(c_black);
        draw_rectangle(bx2, by1, bx2 + bw, by1 + bh, true);
        draw_set_color(button_text_col);
        draw_text_transformed(bx2 + bw * 0.5, by1 + bh * 0.5, "Close", font_scale, font_scale, 0);

        draw_set_halign(fa_left);
        draw_set_valign(fa_top);
        draw_set_color(text_col);

        if (clicked) {
            if (play_hover2) {
                global.current_seeder = preview_map;
                selected_id = string(p_id);
                scr_set_last_selected_id(p_id);
                scr_profile_save(global.profile);
                preview_map = -1;
                room_goto(r_typing);
                return;
            }
            if (close_hover) {
                preview_map = -1;
            }
        }
    } else if (preview_map != -1) {
        preview_map = -1;
    }
}
