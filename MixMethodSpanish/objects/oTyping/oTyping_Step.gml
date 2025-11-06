/// @description Handle typing input, scoring, and progression.
function oTyping_Step() {
    input_text = keyboard_string;
    if (!keyboard_check_pressed(vk_enter)) {
        return;
    }
    if (!is_ds_map(global.current_seeder)) {
        feedback_text = "No seeder ready.";
        return;
    }
    var res = scr_score_ladder(input_text, global.current_seeder);
    var pass = ds_map_find_value(res, "pass");
    var reg_bonus = ds_map_find_value(res, "register_bonus");
    feedback_text = scr_feedback_message(res);

    if (pass) {
        var rewards = -1;
        if (ds_map_exists(global.current_seeder, "rewards")) {
            rewards = ds_map_find_value(global.current_seeder, "rewards");
        }
        if (is_ds_map(rewards)) {
            if (ds_map_exists(rewards, "xp")) {
                global.profile.xp += ds_map_find_value(rewards, "xp");
            }
            var bump = 0;
            if (ds_map_exists(rewards, "mix_bump")) {
                bump = ds_map_find_value(rewards, "mix_bump");
            }
            global.profile.mix_ratio = clamp(global.profile.mix_ratio + bump + reg_bonus, 0, 1);
        } else {
            global.profile.mix_ratio = clamp(global.profile.mix_ratio + reg_bonus, 0, 1);
        }
        if (reg_bonus > 0) {
            global.profile.register_bonus += reg_bonus;
        }
        if (ds_map_exists(global.current_seeder, "id")) {
            var sid = ds_map_find_value(global.current_seeder, "id");
            if (!scr_array_contains(global.profile.seen, sid)) {
                array_push(global.profile.seen, sid);
            }
        }
        scr_log_progress(global.current_seeder, res);
        var next = scr_pick_seeder(global.seeders, global.profile);
        if (next != -1) {
            global.current_seeder = next;
        }
        keyboard_string = "";
        input_text = "";
        scr_profile_save(global.profile);
    }
    ds_map_destroy(res);
}
