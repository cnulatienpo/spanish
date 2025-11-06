/// @function scr_read_text(_path)
/// @description Load an entire text file into a string.
/// @param {string} _path
/// @returns {string}
function scr_read_text(_path) {
    if (!is_string(_path) || _path == "" || !file_exists(_path)) {
        return "";
    }

    var buf = buffer_load(_path);
    if (buf == -1) {
        return "";
    }

    var text = buffer_read(buf, buffer_text);
    buffer_delete(buf);

    return is_string(text) ? text : "";
}
