/// @description Handle search input and scroll for stage select.
function oSelect_Step() {
    if (scr_settings_is_active()) {
        return;
    }

    if (keyboard_check_pressed(vk_backspace)) {
        if (string_length(search_q) > 0) {
            search_q = string_delete(search_q, string_length(search_q), 1);
        }
    }
    var c = keyboard_lastchar;
    if (!(keyboard_check(vk_control) || keyboard_check(vk_alt))) {
        if (c != "" && ord(c) >= 32) {
            search_q += c;
        }
    }

    scroll_y -= mouse_wheel_up() * 40;
    scroll_y += mouse_wheel_down() * 40;
    scroll_y = clamp(scroll_y, 0, max(0, scroll_max));
}
