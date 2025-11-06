/// @description Handle modal interaction shortcuts and refresh logic.
function oBackupMgr_Step() {
    if (keyboard_check_pressed(vk_escape) && active) {
        active = false;
        return;
    }

    if (!active) {
        return;
    }

    if (keyboard_check_pressed(ord("R"))) {
        backups = scr_list_backups();
        if (!scr_array_contains(backups, selected_backup)) {
            selected_backup = (array_length(backups) > 0) ? backups[0] : "";
        }
        files = (selected_backup != "") ? scr_list_backup_files(selected_backup) : [];
        if (!scr_array_contains(files, selected_file)) {
            selected_file = (array_length(files) > 0) ? files[0] : "";
        }
    }
}
