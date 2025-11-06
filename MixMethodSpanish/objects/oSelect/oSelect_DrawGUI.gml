/// @description Render the stage select UI.
function oSelect_DrawGUI() {
    var W = display_get_gui_width();
    var H = display_get_gui_height();

    draw_set_font(f_ui);
    draw_set_color(c_white);
    draw_set_halign(fa_left);

    draw_text(ui_pad, ui_pad, "Mix Method Spanish — Stage Select");
    draw_text(ui_pad, ui_pad + 24, "Search:");
    var search_x1 = ui_pad + 64;
    var search_y1 = ui_pad + 18;
    var search_x2 = search_x1 + 360;
    var search_y2 = search_y1 + 24;
    draw_rectangle(search_x1, search_y1, search_x2, search_y2, false);
    draw_text(search_x1 + 8, search_y1 + 6, search_q);

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
                    var tmp = scr_filter_seeders([peek], search_q);
                    if (array_length(tmp) > 0) {
                        has_match = true;
                        break;
                    }
                }
                if (has_match) {
                    array_push(filtered, entry);
                }
            } else {
                var arr = scr_filter_seeders([entry], search_q);
                if (array_length(arr) > 0) {
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

    var list_x = ui_pad;
    var list_y = ui_pad + 64;
    var list_w = max(220, min(W - ui_pad * 2, col_w));
    var y = list_y - scroll_y;

    var mx = device_mouse_x_to_gui(0);
    var my = device_mouse_y_to_gui(0);
    var clicked = mouse_check_button_pressed(mb_left);

    for (var i2 = 0; i2 < array_length(filtered); i2++) {
        var item = filtered[i2];
        if (is_ds_map(item) && ds_map_exists(item, "__section")) {
            var band = ds_map_find_value(item, "__section");
            draw_set_color(c_silver);
            draw_text(list_x, y, "— " + string(band) + " —");
            y += 26;
            continue;
        }

        var x1 = list_x;
        var x2 = list_x + list_w;
        var y1 = y;
        var y2 = y + card_h;
        var hover = point_in_rectangle(mx, my, x1, y1, x2, y2);
        draw_set_color(hover ? make_color_hsv(210, 15, 35) : make_color_hsv(210, 10, 25));
        draw_rectangle(x1, y1, x2, y2, false);

        var id = ds_map_exists(item, "id") ? ds_map_find_value(item, "id") : "";
        var title = ds_map_exists(item, "title") ? ds_map_find_value(item, "title") : "Untitled";
        var cefr = ds_map_exists(item, "cefr") ? ds_map_find_value(item, "cefr") : "?";
        var tgt = scr_target_label(item);
        var reg = scr_register_label(item);

        draw_set_color(c_white);
        draw_set_halign(fa_left);
        draw_text(x1 + 10, y1 + 8, string(title) + "  (" + string(cefr) + ")");
        draw_text(x1 + 10, y1 + 30, tgt);
        draw_text(x1 + 10, y1 + 48, reg);

        var b_w = 88;
        var b_h = 28;
        var play_x1 = x2 - (b_w * 2 + 24);
        var prev_x1 = x2 - (b_w + 12);
        var by = y1 + card_h - b_h - 8;

        var play_hover = point_in_rectangle(mx, my, play_x1, by, play_x1 + b_w, by + b_h);
        draw_set_color(play_hover ? c_lime : c_dkgray);
        draw_rectangle(play_x1, by, play_x1 + b_w, by + b_h, false);
        draw_set_color(c_white);
        draw_set_halign(fa_center);
        draw_text(play_x1 + b_w / 2, by + b_h / 2 - 6, "Play");

        var preview_hover = point_in_rectangle(mx, my, prev_x1, by, prev_x1 + b_w, by + b_h);
        draw_set_color(preview_hover ? make_color_hsv(40, 60, 80) : c_dkgray);
        draw_rectangle(prev_x1, by, prev_x1 + b_w, by + b_h, false);
        draw_set_color(c_white);
        draw_text(prev_x1 + b_w / 2, by + b_h / 2 - 6, "Preview");
        draw_set_halign(fa_left);

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
            draw_set_color(c_aqua);
            draw_text(x1 + 10, y2 - 20, "Selected");
            draw_set_color(c_white);
        }

        y += card_h + gap_y;
    }

    if (is_ds_map(preview_map)) {
        var w2 = min(560, W - 40);
        var h2 = min(360, H - 80);
        var px = (W - w2) / 2;
        var py = (H - h2) / 2;

        draw_set_color(make_color_hsv(210, 10, 18));
        draw_rectangle(px, py, px + w2, py + h2, false);
        draw_set_color(c_white);
        draw_set_halign(fa_left);

        var p_id = ds_map_exists(preview_map, "id") ? ds_map_find_value(preview_map, "id") : "";
        var p_title = ds_map_exists(preview_map, "title") ? ds_map_find_value(preview_map, "title") : "";
        var p_cefr = ds_map_exists(preview_map, "cefr") ? ds_map_find_value(preview_map, "cefr") : "";
        draw_text(px + 16, py + 14, string(p_title) + " (" + string(p_cefr) + ")");
        draw_text(px + 16, py + 36, scr_target_label(preview_map));
        draw_text(px + 16, py + 56, scr_register_label(preview_map));

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
                draw_text(px + 16, y2, line);
                y2 += 20;
            }
        }

        var bw = 110;
        var bh = 30;
        var bx1 = px + w2 - bw - 16;
        var by1 = py + h2 - bh - 16;
        var bx2 = bx1 - bw - 12;

        var play_hover2 = point_in_rectangle(mx, my, bx1, by1, bx1 + bw, by1 + bh);
        var close_hover = point_in_rectangle(mx, my, bx2, by1, bx2 + bw, by1 + bh);

        draw_set_color(play_hover2 ? c_lime : c_dkgray);
        draw_rectangle(bx1, by1, bx1 + bw, by1 + bh, false);
        draw_set_color(c_white);
        draw_set_halign(fa_center);
        draw_text(bx1 + bw / 2, by1 + bh / 2 - 6, "Play");

        draw_set_color(close_hover ? make_color_hsv(0, 60, 80) : c_dkgray);
        draw_rectangle(bx2, by1, bx2 + bw, by1 + bh, false);
        draw_set_color(c_white);
        draw_text(bx2 + bw / 2, by1 + bh / 2 - 6, "Close");
        draw_set_halign(fa_left);

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
