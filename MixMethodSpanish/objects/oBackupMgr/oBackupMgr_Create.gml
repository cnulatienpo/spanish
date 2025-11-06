/// @description Initialize backup manager modal state.
function oBackupMgr_Create() {
    active = false;
    backups = scr_list_backups();
    selected_backup = (array_length(backups) > 0) ? backups[0] : "";
    files = (selected_backup != "") ? scr_list_backup_files(selected_backup) : [];
    selected_file = (array_length(files) > 0) ? files[0] : "";

    left_scroll = 0;
    right_scroll = 0;
    toast_text = "";
    toast_timer = -1;
}
